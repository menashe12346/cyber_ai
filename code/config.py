# Main Directories paths
PROJECT_PATH = "/mnt/linux-data/project"
WORDLISTS_PATH = "/mnt/linux-data/wordlists"

# Main Directories inside the project
DATASETS_PATH = f"{PROJECT_PATH}/code/datasets"
DATABASES_PATH = f"{PROJECT_PATH}/code/databases"
OS_DATASETS = f"{DATASETS_PATH}/os_datasets"

# Simulation parameters
NUM_EPISODES = 20
MAX_STEPS_PER_EPISODE = 12
EPSILON = 0.6
MAX_ENCODING_FEATURES = 1024

# Target configuration
TARGET_IP = "192.168.56.101" 
#TARGET_IP = "146.190.62.39" 

# Wordlists paths
WORDLISTS = {
    "web_common": f"{WORDLISTS_PATH}/SecLists/Discovery/Web-Content/common.txt"
}

# LLM Model configuration
LLAMA_RUN_PATH = f"{PROJECT_PATH}/code/models/llama.cpp/build/bin/llama-run"
MISTRAL_MODEL_PATH = f"{PROJECT_PATH}/code/models/nous-hermes/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf"


# CACHE CONFIGURATION

# LLM cache path
LLM_CACHE_PATH = f"{PROJECT_PATH}/code/Cache/llm_cache.json"

# Command LLM cache path
COMMAND_LLM_CACHE_PATH = f"{PROJECT_PATH}/code/Cache/command_llm_cache.pkl"

# Correctness cache
CORRECTNESS_CACHE = f"{PROJECT_PATH}/code/Cache/correctness_cache.json"


# DATASETS CONFIGURATION

# NVD cve dataset path
DATASET_NVD_CVE_PATH = f"{DATASETS_PATH}/cve/nvd/nvd_cve_dataset.json"

# NVD cve cpe dataset path
DATASET_NVD_CVE_CPE_PATH = f"{DATASETS_PATH}/cve/nvd/nvd_cve_cpe_dataset.json"

# ExploitDB dataset path
DATASET_EXPLOITDB_CVE_EXPLOIT_PATH = f"{DATASETS_PATH}/exploitdb/exploitdb_dataset(cve,exploit_path).csv"

# ExploitDB files exploits
DATASET_EXPLOITDB_FILES_EXPLOITS_PATH = f"{DATASETS_PATH}/exploitdb/files_exploits.csv"

# Metasploit dataset
DATASET_METASPLOIT = f"{DATASETS_PATH}/metasploit/metasploit_dataset.json"

# Full exploit dataset
DATASET_EXPLOIT = f"{DATASETS_PATH}/exploit_datasets/full_exploit_dataset.json"

# OS Linux dataset
DATASET_OS_LINUX= f"{DATASETS_PATH}/os_datasets/os_linux_dataset.json"

# OS Linux kernel dataset
DATASET_OS_LINUX_KERNEL = f"{DATASETS_PATH}/os_datasets/os_linux_kernel_dataset.json"

#TEMPORARY_FILES

# NVD temporary files path
TEMPORARY_NVD_CVE_PATH = f"{DATASETS_PATH}/cve/nvd/temporary_nvd_files/"

# Temporary Distrowatch files
TEMPORARY_DISTROWATCH_FILES = f"{DATASETS_PATH}/os_datasets/DistroWatch_files/temporary_DistroWatch_files"


# OTHERS

# Distrowatch files
DISTROWATCH_FILES =  f"{PROJECT_PATH}/code/datasets/os_datasets/DistroWatch_files"

# Blackboard path
BLACKBOARD_PATH = f"{PROJECT_PATH}/code/blackboard/blackboard.json"


# STATE CONFIGURATION #

# Web Status codes
EXPECTED_STATUS_CODES = [
    "200", "301", "302", "307", "401", "403", "500", "502", "503", "504"
]

# Default state structure
_BASE_DEFAULT_STATE = {
    "target": {
        "hostname": "",
        "netbios_name": "",
        "os": {
            "name": "",
            "distribution": {"name": "", "version": "", "architecture": ""},
            "kernel": "",
        },
        "services": [
            {
                "port": "", 
                "protocol": "", 
                "service": "", 
                "server_type": "", 
                "server_version": "",
            },
        ],
        "rpc_services": [
            {
                "program_number": "",
                "version": "",
                "protocol": "",
                "port": "",
                "service_name": ""
            }
        ],
        "geo_location": {
            "country": "",
            "region": "",
            "city": "",
        },
        "ssl": {
            "issuer": "",
            "protocols": [""],
        },

    },
    #"web_directories_status": {code: {"": ""} for code in EXPECTED_STATUS_CODES}
}

"""
        "smb_shares": [
        {
          "share_name": "",
          "access": "",
          "comment": ""
        },
      ]
"""

import copy

# Making that every use of default stracture will be with deepcopy
def __getattr__(name):
    if name == "DEFAULT_STATE_STRUCTURE":
        return copy.deepcopy(_BASE_DEFAULT_STATE)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# Web status codes reward
WEB_DIRECTORIES_STATUS_CODES_REWARD = {
    "200": 0.1,
    "301": 0.05,
    "302": 0.05,
    "307": 0.05,
    "401": 0.08,
    "403": 0.1,
    "500": 0.15,
    "502": 0.09,
    "503": 0.09,
    "504": 0.04
}

# state schema ( An explanation of the state). TODO: fix llm_prompt
STATE_SCHEMA = {
  "target": {
    "type": "dict",
  },
  "target.netbios_name": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": (
    "NetBIOS name of the target system, extracted from actual SMB or NetBIOS output "
    "(e.g., via `nbtscan`, `nmap -sU -p137`). Must be a valid machine name, such as 'WIN-7PC123'. "
    "❗ Never return an IP address (e.g., '192.168.x.x'). If no NetBIOS name is found, return 'NO'."
)
  },
  "target.hostname": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.2,
    "llm_prompt": (
    "System-level hostname of the target, as returned by commands like `hostname` or `uname -n`. "
    "Must be a valid machine name such as 'ubuntu-server', 'metasploitable', etc. "
    "⚠️ Never return an IP address like '192.168.56.101'. If no hostname is found, return 'unknown'."
)
  },
  "target.os": {
    "type": "dict",
    "correction_func": "correct_os"
  },
  "target.os.name": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": (
    "General operating system name of the target system, based strictly on scan results or system outputs "
    "(e.g., `nmap -O`, `uname`, NetBIOS banners). Valid values: 'linux', 'windows', 'macos', 'unix'. "
    "❗ Never guess. ❗ Never copy examples. ❗ Never return 'windows' unless explicitly indicated by SMB/NetBIOS/Windows-specific banners. "
    "If unknown, return 'unknown'."
)
  },
  "target.os.distribution": {
    "type": "dict",
    "llm_prompt": "Information about the OS distribution of the target."
  },
  "target.os.distribution.name": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "OS distribution name, e.g., 'ubuntu', 'debian'."
  },
  "target.os.distribution.version": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.05,
    "llm_prompt": (
  "Version of the OS distribution ONLY (e.g., '20.04', '7', '11'). "
  "Do NOT include versions of services, packages, Apache, OpenSSH, BIND, etc. "
  "Return ONLY ONE version string, not multiple versions."
)
  },
  "target.os.distribution.architecture": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "CPU architecture, e.g., 'x86', 'x64'."
  },
  "target.os.kernel": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "Kernel version string, e.g., '6.6.59'."
  },
  "target.services": {
    "type": "list",
    "correction_func": "correct_services",
    "llm_prompt": ""
  },
  "target.services[].port": {
    "type": "int",
    "encoder": "normalize_by_specific_number",
    "num_for_normalization": 65536,
    "reward": 0.1,
    "llm_prompt": "Port number of the service, e.g., 22 or 80."
  },
  "target.services[].protocol": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0,
    "llm_prompt": "Transport protocol used by the service, e.g., 'tcp'."
  },
  "target.services[].service": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "Application-level service name, e.g., 'http', 'ftp'."
  },
  "target.services[].server_type": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "Type of server software, e.g., 'nginx', 'Apache'."
  },
  "target.services[].server_version": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "Version of the server software."
  },
  "target.rpc_services": {
    "type": "list",
    "correction_func": "correct_rpc_services",
    "llm_prompt": ""
  },
  "target.services[].program_number": {
    "type": "int",
    "encoder": "normalize_by_specific_number",
    "num_for_normalization": 999999,
    "reward": 0.1,
    "llm_prompt": "RPC program number associated with the service."
  },
  "target.services[].version": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0,
    "llm_prompt": "Version of the application-level service."
  },
    "target.services[].protocol": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0,
    "llm_prompt": "Transport protocol used by the service, e.g., 'tcp'."
  },
    "target.services[].port": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "Port number of the service, e.g., 22 or 80."
  },
  "target.services[].service_name": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "Name of the service running on this port."
  },
  "target.dns_records": {
    "type": "list",
    "correction_func": "correct_dns_records",
    "llm_prompt": "List of DNS records associated with the target."
  },
  "target.dns_records[].type": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "Type of DNS record, e.g., 'A', 'CNAME', 'MX'."
  },
  "target.dns_records[].value": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0,
    "llm_prompt": "Value associated with the DNS record."
  },
  "target.network_interfaces": {
    "type": "list",
    "correction_func": "correct_network_interfaces",
    "llm_prompt": "List of network interfaces available on the target."
  },
  "target.network_interfaces[].name": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "Name of the network interface, e.g., 'eth0'."
  },
  "target.network_interfaces[].ip_address": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "IPv4 or IPv6 address assigned to this interface."
  },
  "target.network_interfaces[].mac_address": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "MAC address of the network interface."
  },
  "target.network_interfaces[].netmask": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "Netmask/subnet mask, e.g., '255.255.255.0'."
  },
  "target.network_interfaces[].gateway": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "Default gateway for this network interface."
  },
  "target.geo_location": {
    "type": "dict",
    "llm_prompt": "Geolocation data associated with the target IP."
  },
  "target.geo_location.country": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "Country where the target is located."
  },
  "target.geo_location.region": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "Region or state within the country."
  },
  "target.geo_location.city": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.05,
    "llm_prompt": "City of the target system."
  },
  "target.ssl": {
    "type": "dict",
    "llm_prompt": "SSL certificate details of the target (if HTTPS)."
  },
  "target.ssl.issuer": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "Issuer of the SSL certificate."
  },
  "target.ssl.protocols": {
    "type": "list",
    "llm_prompt": "SSL/TLS protocols supported by the target. Must return [] with all the supported protocols, if there isnt any then return empty [""]"
  },
  "target.ssl.protocols[]": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "Supported SSL/TLS protocol versions."
  },


  "target.smb_shares": {
    "type": "dict",
    "llm_prompt": ""
  },

  "target.smb_shares[].share_name": {
      "type": "string",
      "encoder": "base100_encode",
      "reward": 0.1,
      "llm_prompt": "Name of the SMB share as listed by tools like `smbmap`, `smbclient`, or `nmap smb-enum-shares`. Example: 'tmp', 'ADMIN$', 'IPC$'. Do not fabricate or guess names."
  },
  "target.smb_shares[].access": {
      "type": "string",
      "encoder": "base100_encode",
      "reward": 0.1,
      "llm_prompt": "Exact access level reported for the share, such as: 'READ', 'WRITE', 'READ, WRITE', or 'NO ACCESS'. Return exactly what appears in the scan output."
  },
  "target.smb_shares[].comment": {
      "type": "string",
      "encoder": "base100_encode",
      "reward": 0.05,
      "llm_prompt": "Optional description/comment for the share as reported by the server (e.g., 'Printer Drivers', 'IPC Service'). If no comment is provided, return an empty string."
  },


  "target.http_category": {
    "type": "dict",
    "llm_prompt": "Information extracted from HTTP response."
  },
  "target.http_category.headers": {
    "type": "dict",
    "llm_prompt": "Key HTTP headers from the response."
  },
  "target.http_category.headers.Server": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": (
"Extract the web server software name and version from the following HTTP headers."
"Return only the exact value if it clearly appears as a value of a `Server:` HTTP header (e.g., 'Apache/2.4.41')."
"❗ Do NOT extract from `HTTP/1.1 200 OK` — this is the status line, not the server name."
"❗ If the `Server:` header does not exist, return exactly: NO"
"Do NOT guess, explain, expand, or justify anything."
    )
  },
  "target.http_category.headers.X-Powered-By": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.05,
    "llm_prompt": "Technologies reported in the X-Powered-By header, e.g., 'PHP/7.4'."
  },
  "target.http_category.headers.Content-Type": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.05,
    "llm_prompt": "MIME type of the HTTP response, e.g., 'text/html'."
  },
  "target.http_category.title": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.05,
    "llm_prompt": "Title of the web page as seen in the browser tab."
  },
  "target.http_category.robots_txt": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.05,
    "llm_prompt": "Contents of the robots.txt file if present."
  },
  "target.http_category.powered_by": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.05,
    "llm_prompt": "Technologies discovered in meta tags or HTTP headers, e.g., 'WordPress'."
  },
  "target.trust_relationships": {
    "type": "list",
    "llm_prompt": "List of trust relationships between systems or domains."
  },
  "target.trust_relationships[].source": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "The source system or domain in the trust relationship."
  },
  "target.trust_relationships[].target": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "The trusted system or domain in the relationship."
  },
  "target.trust_relationships[].type": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.05,
    "llm_prompt": "Type of trust relationship (e.g., 'one-way', 'transitive')."
  },
  "target.trust_relationships[].direction": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.05,
    "llm_prompt": "Direction of trust: 'inbound' or 'outbound'."
  },
  "target.trust_relationships[].auth_type": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.05,
    "llm_prompt": "Authentication method used in the trust (e.g., 'Kerberos')."
  },
  "target.users": {
    "type": "list",
    "llm_prompt": "List of discovered user accounts."
  },
  "target.users[].username": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.1,
    "llm_prompt": "Username of the account."
  },
  "target.users[].group": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.05,
    "llm_prompt": "Group the user belongs to, e.g., 'Administrators'."
  },
  "target.users[].domain": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.05,
    "llm_prompt": "Domain or hostname associated with the user account."
  },
  "target.groups": {
    "type": "list",
    "llm_prompt": "List of user groups on the system."
  },
  "target.groups[]": {
    "type": "string",
    "encoder": "base100_encode",
    "reward": 0.05,
    "llm_prompt": "Name of the group, e.g., 'Administrators', 'Users'."
  },
  "web_directories_status": {
    "type": "dict",
    "correction_func": "correct_web_directories",
    "llm_prompt": "For each status (200, 403, 401, 404, 503): discovered paths (like '/admin') to their message (or use \"\" if none), format: { \"path\": \"message\" }."
  }
}

# Dynamic addition of status-specific entries
for status in EXPECTED_STATUS_CODES:
    STATE_SCHEMA[f"web_directories_status.{status}"] = {
        "type": "dict",
        "encoder": "count_encoder",
        "reward": WEB_DIRECTORIES_STATUS_CODES_REWARD[status]
    }

STATE_SCHEMA["target.services"]["llm_prompt"] = f"""List of discovered network services on the target system: 
{STATE_SCHEMA.get("target.services[].port")["llm_prompt"]},
{STATE_SCHEMA.get("target.services[].protocol")["llm_prompt"]},
{STATE_SCHEMA.get("target.services[].service")["llm_prompt"]},
{STATE_SCHEMA.get("target.services[].server_type")["llm_prompt"]},
{STATE_SCHEMA.get("target.services[].server_version")["llm_prompt"]}

For example: {{\"port\": \"\", \"protocol\": \"\", \"service\": \"\", \"server_type\": \"\", \"server_version\": \"\"}}, 
{{\"port\": \"\", \"protocol\": \"\", \"service\": \"\", \"server_type\": \"\", \"server_version\": \"\"}}.

And most important: return it as a valid JSON.
Very important: the JSON should be exactly like this in the order — do not change it. At the end, go over it again and check.
Always return with [""] even if there is even one item inside and alweys put "" even if they empty"""


STATE_SCHEMA["target.rpc_services"]["llm_prompt"] = f"""List of detected RPC services running on the target:
{STATE_SCHEMA.get("target.services[].program_number")["llm_prompt"]},
{STATE_SCHEMA.get("target.services[].version")["llm_prompt"]},
{STATE_SCHEMA.get("target.services[].protocol")["llm_prompt"]},
{STATE_SCHEMA.get("target.services[].port")["llm_prompt"]},
{STATE_SCHEMA.get("target.services[].service_name")["llm_prompt"]}

For example: {{\"program_number\": \"\", \"version\": \"\", \"protocol\": \"\", \"port\": \"\", \"service_name\": \"\"}}, 
{{\"program_number\": \"\", \"version\": \"\", \"protocol\": \"\", \"port\": \"\", \"service_name\": \"\"}}.

Return only RPC services discovered via actual RPC-related tools (e.g., `rpcinfo`, `nmap -sU -p 111`, or `showmount`).
Each entry must represent a true RPC program with a valid `program_number` and known RPC service.
⚠️ Do not include regular services like 'http', 'ftp', 'mysql', etc. These are NOT RPC services. 
If no RPC services are found, return an empty list: [""], Do not leave []!!!

And most important: return it as a valid JSON.
Very important: the JSON should be exactly like this in the order — do not change it. At the end, go over it again and check.
Must be RPC services only and not the regular ones
Always return with [""] even if there is even one item inside"""


STATE_SCHEMA["target.smb_shares"]["llm_prompt"] = f"""List of all discovered SMB shares on the target:
{STATE_SCHEMA.get("target.smb_shares[].share_name")["llm_prompt"]},
{STATE_SCHEMA.get("target.smb_shares[].access")["llm_prompt"]},
{STATE_SCHEMA.get("target.smb_shares[].comment")["llm_prompt"]},

For example: {{\"share_name\": \"\", \"access\": \"\", \"comment\": \"\"}}, 
{{\"share_name\": \"\", \"access\": \"\", \"comment\": \"\"}}.

Return only SMB shares discovered via actual SMB-related tools (e.g., `smbmap`, `smbclient`, or `nmap --script smb-enum-shares`).  
Each entry must represent a real SMB share with valid fields: `share_name`, `access`, and `comment`.  
⚠️ Do not include unrelated services like 'http', 'ftp', or 'mysql' — these are NOT SMB shares.  
If no SMB shares are found, return an empty list: [""].

And most important: return it as a valid JSON.
Very important: the JSON should be exactly like this in the order — do not change it. At the end, go over it again and check.
Must be RPC services only and not the regular ones
Always return with [""] even if there is even one item inside and alweys put "" even if they empty"""










SERVICE_FAMILIES = {
    # Remote Access
    "ssh": ["ssh", "openssh", "dropbear"],
    "telnet": ["telnet", "inetutils-telnet"],
    "vnc": ["vnc", "tightvnc", "ultravnc", "realvnc"],
    "rdp": ["rdp", "freerdp", "xrdp", "ms-wbt-server"],

    # FTP Servers 
    "ftp": ["ftp", "vsftpd", "proftpd", "pure-ftpd", "wu-ftpd", "ccproxy-ftp", "bftpd", "serv-u", "filezilla-server"],

    # Web Servers
    "http": ["http", "apache", "nginx", "httpd", "tomcat", "lighttpd", "cherokee", "zeus", "boa", "gws", "thttpd", "jetty", "resin"],
    "https": ["https"] + ["apache", "nginx", "lighttpd", "tomcat", "openssl", "mod_ssl"],

    # SMTP / Mail
    "smtp": ["smtp", "sendmail", "postfix", "exim", "qmail", "hmailserver", "lotus-domino", "mailenable", "mercury"],
    "pop3": ["pop3", "dovecot", "qpopper", "mailenable", "kerio"],
    "imap": ["imap", "dovecot", "courier", "kerio", "lotus-domino"],

    # DNS
    "dns": ["dns", "bind", "named", "powerdns", "unbound", "dnsmasq"],

    # SMB / Windows Networking
    "smb": ["smb", "netbios-ssn", "microsoft-ds", "samba", "cifs"],
    "nbns": ["nbns", "nbt", "netbios", "netbios-ns"],
    "rpc": ["rpc", "rpcbind", "portmap", "msrpc"],

    # Databases
    "mysql": ["mysql", "mariadb", "percona"],
    "postgresql": ["postgresql", "postgres"],
    "mssql": ["mssql", "sqlserver", "microsoft-sql"],
    "oracle": ["oracle", "oracle-db", "tns", "oracle-listener"],
    "redis": ["redis"],
    "mongodb": ["mongodb"],
    "db2": ["db2"],
    "couchdb": ["couchdb"],

    # Web Frameworks & CMS
    "php": ["php"],
    "wordpress": ["wordpress", "wp"],
    "drupal": ["drupal"],
    "joomla": ["joomla"],
    "django": ["django"],
    "rails": ["rails", "ruby-on-rails"],
    "struts": ["struts", "apache-struts"],

    # Remote Management
    "snmp": ["snmp", "net-snmp"],
    "nfs": ["nfs", "rpc.mountd", "rpc.nfsd"],
    "rlogin": ["rlogin"],
    "rsh": ["rsh"],
    "x11": ["x11", "xorg", "xdmcp"],

    # Proxy / Reverse Proxy / Load Balancer
    "squid": ["squid", "squid-cache"],
    "haproxy": ["haproxy"],
    "nginx": ["nginx"],

    # Java / Middleware / Application Servers
    "tomcat": ["tomcat", "apache-tomcat"],
    "jboss": ["jboss", "wildfly"],
    "weblogic": ["weblogic", "oracle-weblogic"],
    "glassfish": ["glassfish"],
    "websphere": ["websphere", "ibm-websphere"],
    "resin": ["resin"],

    # Development Tools
    "git": ["git", "gitlab", "gitea"],
    "svn": ["svn", "subversion"],
    "jenkins": ["jenkins"],
    "docker": ["docker", "docker-engine"],
    "kubernetes": ["kubernetes", "k8s", "api-server"],

    # IoT / Embedded
    "upnp": ["upnp"],
    "ssdp": ["ssdp"],
    "telnetd": ["telnetd", "busybox"],
    "webcam": ["webcam", "ipcam", "dvr", "nvr"],

    # SCADA / Industrial
    "modbus": ["modbus"],
    "dnp3": ["dnp3"],
    "opc": ["opc", "opc-ua"],
    "siemens": ["s7", "siemens"],

    # VPN / Tunnels
    "openvpn": ["openvpn"],
    "pptp": ["pptp"],
    "ipsec": ["ipsec", "strongswan", "openswan", "libreswan"],

    # Misc
    "ajp13": ["ajp13", "apache-jserv-protocol"],
    "ldap": ["ldap", "openldap", "389ds", "activedirectory"],
    "kerberos": ["kerberos", "kdc"],
    "cups": ["cups", "ipp"],
    "ntp": ["ntp", "ntpd"],
    "dhcp": ["dhcp", "dhcpd", "isc-dhcp"],
    "tftp": ["tftp", "atftpd"],
    "rsync": ["rsync"],
    "xinetd": ["xinetd"],
}
