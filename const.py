DOMAIN = "fmc130_traccar"

# Device Config
CONF_IMEI = "imei"
CONF_DEVICE_NAME = "device_name"

# Direct Listener Config
CONF_LISTENER_PORT = "listener_port"
CONF_TLS_ENABLED = "tls_enabled"
CONF_TLS_MODE = "tls_mode"
CONF_SSL_CERT = "ssl_cert"
CONF_SSL_KEY = "ssl_key"
CONF_DEBUG_MODE = "debug_mode"

TLS_MODE_NONE = "none"
TLS_MODE_HA = "home_assistant"
TLS_MODE_CUSTOM = "custom"

DEFAULT_PORT = 8082
DEFAULT_LISTENER_PORT = 5027
DEFAULT_USE_SSL = True

CONF_MAPPING_RPM = "map_rpm"
CONF_MODIFIER_RPM = "mod_rpm"
CONF_MAPPING_FUEL = "map_fuel"
CONF_MODIFIER_FUEL = "mod_fuel"
CONF_MAPPING_OIL = "map_oil"
CONF_MODIFIER_OIL = "mod_oil"
CONF_MAPPING_DTC = "map_dtc"
CONF_MODIFIER_DTC = "mod_dtc"

CONF_MAPPING_DOOR_FL = "map_door_fl"
CONF_MODIFIER_DOOR_FL = "mod_door_fl"
CONF_MAPPING_DOOR_FR = "map_door_fr"
CONF_MODIFIER_DOOR_FR = "mod_door_fr"
CONF_MAPPING_DOOR_RL = "map_door_rl"
CONF_MODIFIER_DOOR_RL = "mod_door_rl"
CONF_MAPPING_DOOR_RR = "map_door_rr"
CONF_MODIFIER_DOOR_RR = "mod_door_rr"
CONF_MAPPING_LOCKED = "map_locked"
CONF_MODIFIER_LOCKED = "mod_locked"
CONF_MAPPING_WINDOWS = "map_windows"
CONF_MODIFIER_WINDOWS = "mod_windows"
CONF_MAPPING_HANDBRAKE = "map_handbrake"
CONF_MODIFIER_HANDBRAKE = "mod_handbrake"
CONF_MAPPING_LIGHTS = "map_lights"
CONF_MODIFIER_LIGHTS = "mod_lights"

DEFAULT_MAPPINGS = {
    CONF_MAPPING_RPM: "85",
    CONF_MAPPING_FUEL: "84",
    CONF_MAPPING_OIL: "235",
    CONF_MAPPING_DTC: "282", # Typical DTC IO
    CONF_MAPPING_DOOR_FL: "654",
    CONF_MAPPING_DOOR_FR: "655",
    CONF_MAPPING_DOOR_RL: "656",
    CONF_MAPPING_DOOR_RR: "657",
    CONF_MAPPING_LOCKED: "662",
    CONF_MAPPING_WINDOWS: "", # Varies widely, let user configure if present
    CONF_MAPPING_HANDBRAKE: "653",
    CONF_MAPPING_LIGHTS: "965", # Lights Failure
}

DEFAULT_MODIFIERS = {
    CONF_MODIFIER_RPM: "",
    CONF_MODIFIER_FUEL: "*0.1",
    CONF_MODIFIER_OIL: "",
    CONF_MODIFIER_DTC: "",
    CONF_MODIFIER_DOOR_FL: "",
    CONF_MODIFIER_DOOR_FR: "",
    CONF_MODIFIER_DOOR_RL: "",
    CONF_MODIFIER_DOOR_RR: "",
    CONF_MODIFIER_LOCKED: "",
    CONF_MODIFIER_WINDOWS: "",
    CONF_MODIFIER_HANDBRAKE: "",
    CONF_MODIFIER_LIGHTS: "",
}
