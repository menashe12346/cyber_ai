import random
import subprocess
import json
import torch
import os
import sys
import numpy as np
from abc import ABC, abstractmethod
from typing import Any, List
from time import sleep
from config import DEFAULT_STATE_STRUCTURE

from blackboard.blackboard import initialize_blackboard

from Cache.llm_cache import LLMCache
from Cache.commandLLM_cache import CommandLLMCache

from utils.prompts import PROMPT, PROMPT_FOR_A_PROMPT
from utils.utils import remove_comments_and_empty_lines
from utils.state_check.state_validator import validate_state
from utils.state_check.state_correctness import correct_state, clean_state, merge_state
from utils.state_check.state_sorting import sort_state
from utils.json_fixer import fix_json
from tools.run_manual import run_clean_output

def remove_untrained_categories(state: dict, trained_categories: dict):

    keys_to_remove = [key for key in state if key not in trained_categories]
    for key in keys_to_remove:
        state.pop(key, None)

    for key, allowed_fields in trained_categories.items():
        if allowed_fields is None:
            continue
        if key in state and isinstance(state[key], dict):
            inner_keys_to_remove = [inner_key for inner_key in state[key] if inner_key not in allowed_fields]
            for inner_key in inner_keys_to_remove:
                state[key].pop(inner_key, None)

def is_valid_json(s: str) -> bool:
    try:
        json.loads(s)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents in the attack environment.
    Provides the main learning and acting loop, caching, output parsing, and interaction with the blackboard.
    """

    def __init__(self, name, action_space, blackboard_api, replay_buffer,
                 policy_model, state_encoder, action_encoder, command_cache, model, epsilon, os_linux_dataset, os_linux_kernel_dataset, min_epsilon = 0.01, epsilon_decay = 0.995):
        self.name = name
        self.action_space = action_space
        self.blackboard_api = blackboard_api
        self.replay_buffer = replay_buffer
        self.policy_model = policy_model
        self.state_encoder = state_encoder
        self.action_encoder = action_encoder
        self.command_cache = command_cache
        self.model = model
        self.epsilon = epsilon
        self.min_epsilon = min_epsilon
        self.epsilon_decay = epsilon_decay
        self.actions_history = []
        self.last_state = None
        self.encoded_last_state = None
        self.last_action = None
        self.llm_cache = LLMCache()
        self.command_llm_cache = CommandLLMCache()
        self.episode_total_reward = 0.0
        self.os_linux_dataset=os_linux_dataset,
        self.os_linux_kernel_dataset=os_linux_kernel_dataset

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")  # <-- חדש
 
    @abstractmethod
    def should_run(self) -> bool:
        """
        Must be implemented by subclasses to decide whether the agent should act now.
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_reward(self, prev_state, action, next_state) -> float:
        """
        Must be implemented by subclasses to compute the reward signal.
        """
        raise NotImplementedError

    def run(self):
        """
        Main loop of the agent: observe, choose action, perform, parse, learn, update.
        """
        #step 1: fill state with all categories
        self.blackboard_api.fill_state(
            actions_history=self.actions_history.copy(),
            )
        # Step 1: get state
        state = dict(self.get_state_raw())
        encoded_state = self.state_encoder.encode(state, self.actions_history)
        self.last_state = state
        self.encoded_last_state = encoded_state

        # [DEBUG]
        #print(f"last state: {json.dumps(state, indent=2)}")

        # Step 2: select action
        action = self.choose_action(encoded_state)
        self.last_action = action

        #print(f"\n[+] Agent: {self.name}")
        #print(f"    Current state: {str(state)[:8]}...")
        print(f"    Chosen action: {action}")

        # Step 3: execute action
        result = remove_comments_and_empty_lines(self.perform_action(action)) # TODO: Improving remove_comments_and_empty_lines
        #print("\033[1;32m" + str(result) + "\033[0m")

        # Step 4: clean output (if long)
        """
        if len(result.split()) > 300:
            try:
                cleaned_output = self.clean_output(clean_output_prompt(result))
            except Exception as e:
                print(f"[!] Failed to clean output: {e}")
                cleaned_output = result
        else:
            cleaned_output = result
        print(f"\033[94mcleaned_output - {cleaned_output}\033[0m")
        """

        # Step 5: parse, validate and update blackboard
        self.parse_output(result)
        #print(f"parsed_info - {parsed_info}")

        #sleep(1)

        new_info = self.llm_cache.get(action)
        new_info = self.update_state_with_categories(self.last_state, new_info)
        #print(f"new_info - {new_info}")
        self.check_state(new_info)
        #print(f"after - {new_info}")

        self.blackboard_api.update_state(self.name, new_info)

        # Step 6: observe next state
        next_state = dict(self.get_state_raw())
        encoded_next_state = self.state_encoder.encode(next_state, self.actions_history)

        # Step 7: reward and update model
        reward = self.get_reward(state, action, next_state, new_info)
        self.episode_total_reward += reward
        #print(f"new state: {json.dumps(dict(self.state_encoder.decode(encoded_next_state)), indent=2)}")

        self.actions_history.append(action)

        experience = {
            "state": encoded_state,
            "action": self.action_space.index(action),
            "reward": reward,
            "next_state": encoded_next_state
        }

        q_pred, loss = self.policy_model.update(experience)

        #print(f"    Predicted Q-value: {q_pred:.4f}")
        #print(f"    Actual reward:     {reward:.4f}")
        #print(f"    Loss:              {loss:.6f}")

        # Step 8: save experience
        if self.replay_buffer is not None:
            self.replay_buffer.add_experience(encoded_state, self.action_space.index(action), reward, encoded_next_state, False)

        # Step 9: log action
        self.blackboard_api.append_action_log({
            "agent": self.name,
            "action": action,
            "result": result,
        })

    def choose_action(self, state_vector):
        """
        ε-greedy policy: choose random action with probability ε, else best predicted action.
        Also prints all predicted Q-values for analysis.
        """
        # הפוך את state_vector ל־Tensor אם צריך
        if not isinstance(state_vector, torch.Tensor):
            state_tensor = torch.tensor(state_vector, dtype=torch.float32).unsqueeze(0)
        else:
            state_tensor = state_vector.unsqueeze(0) if state_vector.ndim == 1 else state_vector

        state_tensor = state_tensor.to(next(self.policy_model.parameters()).device)

        # חיזוי Q-values
        with torch.no_grad():
            q_values = self.policy_model.forward(state_tensor).cpu().numpy().flatten()

        # הדפסה של כל הערכים
        #print("\n[✓] Q-value predictions:")
        #for action, q in zip(self.action_space, q_values):
            #print(f"  {action:70s} => Q = {q:.4f}")

        # בחירת פעולה
        rnd = random.random() 
        if rnd < self.epsilon:
            #print(f"\033[91m[! EXPLORATION] rnd={rnd:.4f} < ε={self.epsilon:.4f} → Choosing random action\033[0m")
            action_index = random.randint(0, len(self.action_space) - 1)
        else:
            action_index = int(np.argmax(q_values))

        return self.action_space[action_index]

    def decay_epsilon(self):
        """
        Gradually reduce exploration probability.
        """
        self.epsilon = max(self.epsilon * self.epsilon_decay, self.min_epsilon)

    def get_state_raw(self):
        """
        Get the current blackboard state as-is (used for encoding).
        """
        return self.blackboard_api.get_state_for_agent(self.name)

    def get_state(self):
        """
        Encoded state vector.
        """
        return self.state_encoder.encode(self.get_state_raw(), self.actions_history)

    def perform_action(self, action: str) -> str:
        """
        Default behavior: run an IP-based shell command with the action template.
        """
        ip = self.blackboard_api.blackboard.get("target", {}).get("ip", "127.0.0.1")
        command = action.format(ip=ip)

        if action in self.command_cache:
            #print(f"[Cache] Returning cached result for action: {action}")
            return self.command_cache[action]
        
        try:
            #output = subprocess.check_output(command.split(), timeout=10).decode()
            output = run_clean_output(command, timeout=60*5)
            #print(f"output: {output}")
        except Exception as e:
            self.blackboard_api.add_error(self.name, action, str(e))
            output = ""

        self.command_cache[action] = output
        return output
        
    def parse_output(self, command_output: str, context_num=1, retries: int = 1):
        """
        Parse command output using the LLM. Each trained category (including nested ones)
        gets its own prompt. Caching is done per action::category_path.
        """

        trained_categories = {
            "target": {
                "hostname", "netbios_name", "os", "services", "rpc_services", "dns_records",
                "network_interfaces", "geo_location", "ssl", "http", "trust_relationships",
                "users", "groups"
            },
            "web_directories_status": None
        }

        def extract_paths(d: Any, prefix: str = "", include_brackets: bool = False) -> list[str]:
            """
            Extracts paths from a nested dictionary structure.
            
            - Lists are treated as leaf nodes — no recursion into list elements.
            - If include_brackets=True, list fields will be marked with '[]' (e.g., 'services[]').
            - All paths use '::' as separator.

            Args:
                d (Any): The input structure (typically a nested dict).
                prefix (str): The path prefix used during recursion.
                include_brackets (bool): Whether to append '[]' for lists.

            Returns:
                list[str]: List of paths as strings.
            """
            paths = []

            if isinstance(d, dict):
                for key, val in d.items():
                    current_path = f"{prefix}::{key}" if prefix else key
                    if isinstance(val, list):
                        # Treat list as a leaf
                        list_path = current_path + "[]" if include_brackets else current_path
                        paths.append(list_path)
                    else:
                        paths.extend(extract_paths(val, current_path, include_brackets))

            elif isinstance(d, set):
                fake_dict = {key: None for key in d}
                paths.extend(extract_paths(fake_dict, prefix, include_brackets))

            else:
                paths.append(prefix)

            return paths

        def extract_model_response(raw: str) -> str:
            """
            מחלץ את הפלט האמיתי של המודל לפי תבנית escape קבועה,
            ע"י זיהוי התחלה: 'Loading model\\n\\u001b[K\\n\\u001b[33m'
            וסיום: '\\u001b[0m\\n\\u001b[0m\\n'
            """
            start_marker = "Loading model\n\u001b[K\n\u001b[33m"
            end_marker = "\u001b[0m\n\u001b[0m\n"

            start_index = raw.find(start_marker)
            if start_index == -1:
               # print("[!] Start marker not found.")
                return ""

            # המיקום שבו מתחילה התשובה
            answer_start = start_index + len(start_marker)

            end_index = raw.find(end_marker, answer_start)
            if end_index == -1:
                print("[!] End marker not found.")
                return raw[answer_start:].strip()

            # חותכים בדיוק בין ההתחלה לסיום
            return raw[answer_start:end_index].strip()

        category_paths = extract_paths(DEFAULT_STATE_STRUCTURE)
        full_responses = {}

        for cat_path in category_paths:
            key = f"{self.last_action}::{cat_path}"
            cached_response = self.llm_cache.get(key)

            if cached_response:
                #print(f"\033[93m[CACHE] Using cached response for {cat_path}\033[0m")
                response = cached_response if isinstance(cached_response, str) else json.dumps(cached_response)
            else:
                prompt = PROMPT(command_output, cat_path.replace("::", "."))
                response = self.model.run(prompt, context_num)
                response = extract_model_response(response)
                if is_valid_json(response):
                    response_list = json.loads(response)
                    # ודא שזו באמת רשימה
                    if isinstance(response_list, list):
                        # שמור במטמון
                        self.llm_cache.set(key, response_list)
                        continue

                response = response.strip()
                self.llm_cache.set(key, response)

            full_responses[cat_path] = response

        combined_response = "\n".join(full_responses.values())
        #print(f"[✓] Combined model response length: {len(combined_response)} characters.")
        #print(f"[DEBUG] full_response - {combined_response}")
    
    def update_state_with_categories(self, state: dict, categories: dict) -> dict:
        """
        Recursively updates the `state` dict using values from `categories`.
        - Only fills in values that are currently empty in `state`.
        - If a value in `categories` is 'NO', it is ignored.
        - Lists are merged: new values are added if they don't already exist.
        - Works in-place on a copy of `state` and returns the new state.
        """
        import copy
        updated = copy.deepcopy(state)  # כדי לא לשנות את המקור

        def recurse(state_node, category_node):
            if isinstance(category_node, dict) and isinstance(state_node, dict):
                for key, cat_val in category_node.items():
                    if key not in state_node:
                        continue  # התעלם ממפתחות שלא קיימים ב־state

                    state_val = state_node[key]

                    if isinstance(cat_val, dict):
                        recurse(state_val, cat_val)

                    elif isinstance(cat_val, list) and isinstance(state_val, list):
                        if cat_val == "NO":
                            continue
                        # רק מוסיף פריטים חדשים לרשימה מבלי למחוק קיימים
                        for item in cat_val:
                            if item not in state_val:
                                state_val.append(item)

                    elif cat_val != "NO":
                        # עדכן רק אם הערך הנוכחי ב־state ריק ("" או None)
                        if state_val in ["", None]:
                            state_node[key] = cat_val

            return

        recurse(updated, categories)
        return updated

    def clean_output(self, command_output: str) -> dict:
        """
        Clean long noisy outputs using a cleanup prompt and the LLM.
        """
        return self.model.run_prompt(clean_output_prompt(command_output))

    def update_policy(self, state, action, reward, next_state):
        """
        Manually trigger an update to the Q-network.
        """
        self.policy_model.update({
            "state": state,
            "action": self.action_space.index(action),
            "reward": reward,
            "next_state": next_state
        })

    def check_state(self, current_state: str):
        # Validate and correct the state
        #new_state = validate_state(current_state)
        #print(f"[DEBUG] validate_state: {new_state}")
        
        #new_state = merge_state(new_state)
        #print(f"[DEBUG] merge_state: {new_state}")
        
        # Correct the state based on predefined rules
        #new_state = new_state = correct_state(state=new_state, os_linux_dataset=self.os_linux_dataset, os_linux_kernel_dataset=self.os_linux_kernel_dataset)
        #print(f"[DEBUG] correct_state: {new_state}")

        new_state = clean_state(current_state, initialize_blackboard())

        # Ensure the state is a dictionary
        if not isinstance(new_state, dict):
           # print(f"[!] Warning: Invalid state type received. Converting to dictionary...")
            new_state = dict(new_state)
        
        new_state = sort_state(new_state)
        #print(f"[DEBUG] sort_state: {new_state}")

        return new_state
