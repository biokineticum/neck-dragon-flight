# ==============================================================================
# InputManager.gd - Dual-Mode UDP Telemetry Receiver & Keyboard/Mouse Blending
# ==============================================================================
# Milestone 3 / Interface Contracts 1 & 2:
# - Receives head-tracking telemetry datagrams via non-blocking PacketPeerUDP on 127.0.0.1:42425
# - Parses JSON payload: {"pitch": float, "yaw": float, "roll": float, "calibrated": bool, "tracking": bool}
# - Normalizes steering degrees into [-1.0, 1.0] (pitch: [-35, 35], yaw: [-45, 45], roll: [-35, 35])
# - Automatically detects packet timeout (>0.5s) and decays signals toward 0.0 at rate 8.0 * delta
# - Seamless dual-mode fallback: keyboard/mouse immediately commands 100% authority; on release smoothly crossfades back over 0.35s
# - Runtime 'C' hotkey calibration to zero neutral pose
# ==============================================================================
class_name InputManager
extends Node

# Telemetry and Calibration Signals (Feature 16)
signal telemetry_status_changed(new_status: String)
signal calibration_triggered()

# Interface Contract 1 Constants
const UDP_HOST: String = "127.0.0.1"
const UDP_PORT: int = 42425
const PACKET_TIMEOUT_SEC: float = 0.50
const DECAY_RATE: float = 8.0
const CROSSFADE_DURATION: float = 0.35

const MAX_PITCH_DEG: float = 35.0
const MAX_YAW_DEG: float = 45.0
const MAX_ROLL_DEG: float = 35.0

# Network
var udp_server: PacketPeerUDP = PacketPeerUDP.new()
var is_socket_bound: bool = false
var last_bind_attempt: float = -5.0

# Telemetry State
var head_tracking_active: bool = false
var time_since_last_packet: float = 999.0
var raw_pitch_deg: float = 0.0
var raw_yaw_deg: float = 0.0
var raw_roll_deg: float = 0.0
var last_packet_tracking: bool = false
var last_packet_calibrated: bool = false
var calibration_flash_timer: float = 0.0

# Neutral Calibration Offsets
var neutral_pitch_deg: float = 0.0
var neutral_yaw_deg: float = 0.0
var neutral_roll_deg: float = 0.0

# Configuration & Persistence
const SETTINGS_FILE_PATH: String = "user://input_settings.cfg"

# Sensitivity & Control Customization
@export var sensitivity_overall: float = 1.0
@export var sensitivity_yaw: float = 1.0
@export var sensitivity_pitch: float = 1.0
@export var sensitivity_roll: float = 1.0
@export var invert_pitch: bool = false
@export var invert_yaw: bool = false

# Normalized Signals [-1.0, 1.0]
var webcam_pitch: float = 0.0
var webcam_yaw: float = 0.0
var webcam_roll: float = 0.0

# Dual-Mode Blending State
var current_control_mode: String = "KEYBOARD_MOUSE"
var manual_controls_were_active: bool = false
var is_crossfading: bool = false
var crossfade_time: float = 0.0
var blend_start_pitch: float = 0.0
var blend_start_yaw: float = 0.0
var blend_start_roll: float = 0.0

var final_pitch: float = 0.0
var final_yaw: float = 0.0
var final_roll: float = 0.0

# Programmatic Test Simulation Hooks
var simulated_input_active: bool = false
var simulated_pitch: float = 0.0
var simulated_yaw: float = 0.0
var simulated_roll: float = 0.0

func _ready() -> void:
	load_settings()
	bind_socket()

func _exit_tree() -> void:
	close_socket()

func bind_socket() -> bool:
	if udp_server.is_bound():
		return true
	var err = udp_server.bind(UDP_PORT, UDP_HOST)
	if err != OK:
		err = udp_server.bind(UDP_PORT, "*")
	if err == OK:
		is_socket_bound = true
		return true
	else:
		push_warning("InputManager: Failed to bind UDP on %s:%d (error %d)" % [UDP_HOST, UDP_PORT, err])
		is_socket_bound = false
		return false

func close_socket() -> void:
	if udp_server and udp_server.is_bound():
		udp_server.close()
	is_socket_bound = false

func _physics_process(delta: float) -> void:
	poll_packets()
	update_inputs(delta)

func _process(_delta: float) -> void:
	if Input.is_action_just_pressed("calibrate"):
		calibrate_neutral()

func poll_packets() -> void:
	if not is_socket_bound:
		var now_sec = Time.get_ticks_msec() / 1000.0
		if now_sec - last_bind_attempt >= 1.0:
			last_bind_attempt = now_sec
			bind_socket()
		if not is_socket_bound:
			return

	var received: bool = false
	var had_tracking: bool = false
	while udp_server.get_available_packet_count() > 0:
		var pkt = udp_server.get_packet()
		var txt = pkt.get_string_from_utf8()
		if process_json_packet(txt):
			received = true
			had_tracking = last_packet_tracking

	if received:
		if had_tracking:
			time_since_last_packet = 0.0
			head_tracking_active = true
		else:
			head_tracking_active = false

static func _extract_float(val: Variant) -> float:
	if typeof(val) == TYPE_FLOAT or typeof(val) == TYPE_INT:
		return float(val)
	elif typeof(val) == TYPE_STRING and (val as String).is_valid_float():
		return float(val)
	return 0.0

static func _extract_bool(val: Variant, default_val: bool = true) -> bool:
	if typeof(val) == TYPE_BOOL:
		return val as bool
	elif typeof(val) == TYPE_INT or typeof(val) == TYPE_FLOAT:
		return float(val) != 0.0
	elif typeof(val) == TYPE_STRING:
		var s = (val as String).to_lower().strip_edges()
		if s == "false" or s == "0":
			return false
		elif s == "true" or s == "1":
			return true
	elif typeof(val) == TYPE_NIL:
		return default_val
	return default_val

func process_json_packet(text: String) -> bool:
	var json = JSON.new()
	var err = json.parse(text)
	if err != OK or typeof(json.data) != TYPE_DICTIONARY:
		return false
	
	var data: Dictionary = json.data
	last_packet_tracking = _extract_bool(data.get("tracking"), true)
	last_packet_calibrated = _extract_bool(data.get("calibrated"), false)
	# Safe field extraction with fallback (replaces vulnerable raw_pitch_deg = float(data.get("pitch", 0.0)))
	# raw_pitch_deg = float(data.get("pitch", 0.0))
	# raw_yaw_deg = float(data.get("yaw", 0.0))
	# raw_roll_deg = float(data.get("roll", 0.0))
	raw_pitch_deg = _extract_float(data.get("pitch", 0.0))
	raw_yaw_deg = _extract_float(data.get("yaw", 0.0))
	raw_roll_deg = _extract_float(data.get("roll", 0.0))
	
	if last_packet_tracking:
		var eff_pitch = (raw_pitch_deg - neutral_pitch_deg) * sensitivity_pitch * sensitivity_overall
		var eff_yaw = (raw_yaw_deg - neutral_yaw_deg) * sensitivity_yaw * sensitivity_overall
		var eff_roll = (raw_roll_deg - neutral_roll_deg) * sensitivity_roll * sensitivity_overall
		
		if invert_pitch:
			eff_pitch = -eff_pitch
		if invert_yaw:
			eff_yaw = -eff_yaw
		
		webcam_pitch = clampf(eff_pitch / MAX_PITCH_DEG, -1.0, 1.0)
		webcam_yaw = clampf(eff_yaw / MAX_YAW_DEG, -1.0, 1.0)
		webcam_roll = clampf(eff_roll / MAX_ROLL_DEG, -1.0, 1.0)
	else:
		head_tracking_active = false
	return true

func update_inputs(delta: float) -> void:
	if calibration_flash_timer > 0.0:
		calibration_flash_timer -= delta
		
	time_since_last_packet += delta
	if time_since_last_packet > PACKET_TIMEOUT_SEC:
		head_tracking_active = false

	if not is_webcam_active():
		webcam_pitch = move_toward(webcam_pitch, 0.0, DECAY_RATE * delta)
		webcam_yaw = move_toward(webcam_yaw, 0.0, DECAY_RATE * delta)
		webcam_roll = move_toward(webcam_roll, 0.0, DECAY_RATE * delta)

	var manual_pitch: float = 0.0
	var manual_yaw: float = 0.0
	var manual_roll: float = 0.0
	var is_manual_pressed: bool = false
	
	if simulated_input_active:
		manual_pitch = clampf(simulated_pitch, -1.0, 1.0)
		manual_yaw = clampf(simulated_yaw, -1.0, 1.0)
		manual_roll = clampf(simulated_roll, -1.0, 1.0)
		is_manual_pressed = (absf(manual_pitch) > 0.01 or absf(manual_yaw) > 0.01 or absf(manual_roll) > 0.01)
	else:
		manual_pitch = Input.get_axis("steer_pitch_down", "steer_pitch_up")
		manual_yaw = Input.get_axis("steer_yaw_left", "steer_yaw_right")
		manual_roll = Input.get_axis("steer_roll_left", "steer_roll_right")
		is_manual_pressed = (absf(manual_pitch) > 0.01 or absf(manual_yaw) > 0.01 or absf(manual_roll) > 0.01)

	var webcam_ok = is_webcam_active()

	if is_manual_pressed:
		manual_controls_were_active = true
		is_crossfading = false
		crossfade_time = 0.0
		current_control_mode = "KEYBOARD_MOUSE"
		final_pitch = manual_pitch
		final_yaw = manual_yaw
		final_roll = manual_roll
	elif not webcam_ok:
		if absf(webcam_pitch) > 0.001 or absf(webcam_yaw) > 0.001 or absf(webcam_roll) > 0.001:
			current_control_mode = "BLENDED"
			final_pitch = webcam_pitch
			final_yaw = webcam_yaw
			final_roll = webcam_roll
		else:
			manual_controls_were_active = false
			is_crossfading = false
			crossfade_time = 0.0
			current_control_mode = "KEYBOARD_MOUSE"
			final_pitch = manual_pitch
			final_yaw = manual_yaw
			final_roll = manual_roll
	else:
		# Manual released and webcam is active
		if manual_controls_were_active:
			manual_controls_were_active = false
			is_crossfading = true
			crossfade_time = 0.0
			blend_start_pitch = final_pitch
			blend_start_yaw = final_yaw
			blend_start_roll = final_roll
			current_control_mode = "BLENDED"

		if is_crossfading:
			crossfade_time += delta
			var t = clampf(crossfade_time / CROSSFADE_DURATION, 0.0, 1.0)
			if t < 1.0:
				current_control_mode = "BLENDED"
				final_pitch = lerpf(blend_start_pitch, webcam_pitch, t)
				final_yaw = lerpf(blend_start_yaw, webcam_yaw, t)
				final_roll = lerpf(blend_start_roll, webcam_roll, t)
			else:
				is_crossfading = false
				current_control_mode = "WEBCAM"
				final_pitch = webcam_pitch
				final_yaw = webcam_yaw
				final_roll = webcam_roll
		else:
			current_control_mode = "WEBCAM"
			final_pitch = webcam_pitch
			final_yaw = webcam_yaw
			final_roll = webcam_roll

# Interface Contract 2 Public API
func get_pitch_input() -> float:
	return final_pitch

func get_yaw_input() -> float:
	return final_yaw

func get_roll_input() -> float:
	return final_roll

func is_webcam_active() -> bool:
	return head_tracking_active and (time_since_last_packet <= PACKET_TIMEOUT_SEC)

func get_control_mode() -> String:
	return current_control_mode

func is_boost_pressed() -> bool:
	return Input.is_action_pressed("boost")

func is_brake_pressed() -> bool:
	return Input.is_action_pressed("brake")

func calibrate_neutral() -> void:
	if is_webcam_active():
		neutral_pitch_deg = raw_pitch_deg
		neutral_yaw_deg = raw_yaw_deg
		neutral_roll_deg = raw_roll_deg
	else:
		neutral_pitch_deg = 0.0
		neutral_yaw_deg = 0.0
		neutral_roll_deg = 0.0
	calibration_flash_timer = 1.5
	calibration_triggered.emit()
	telemetry_status_changed.emit(get_telemetry_status())

func get_telemetry_status() -> String:
	if not is_webcam_active():
		return "FALLBACK"
	if not last_packet_calibrated or calibration_flash_timer > 0.0:
		return "CALIBRATING"
	return "TRACKING"

func reset_calibration() -> void:
	neutral_pitch_deg = 0.0
	neutral_yaw_deg = 0.0
	neutral_roll_deg = 0.0

func inject_telemetry_packet(data: Dictionary) -> void:
	var json_str = JSON.stringify(data)
	if process_json_packet(json_str):
		if last_packet_tracking:
			time_since_last_packet = 0.0
			head_tracking_active = true
		else:
			head_tracking_active = false

func set_simulated_keyboard_input(pitch: float, yaw: float, roll: float, active: bool = true) -> void:
	simulated_pitch = pitch
	simulated_yaw = yaw
	simulated_roll = roll
	simulated_input_active = active

# ==============================================================================
# Sensitivity Customization & Persistence
# ==============================================================================

func set_sensitivity_overall(val: float) -> void:
	sensitivity_overall = clampf(val, 0.1, 5.0)
	save_settings()

func set_sensitivity_yaw(val: float) -> void:
	sensitivity_yaw = clampf(val, 0.1, 5.0)
	save_settings()

func set_sensitivity_pitch(val: float) -> void:
	sensitivity_pitch = clampf(val, 0.1, 5.0)
	save_settings()

func set_sensitivity_roll(val: float) -> void:
	sensitivity_roll = clampf(val, 0.1, 5.0)
	save_settings()

func set_invert_pitch(val: bool) -> void:
	invert_pitch = val
	save_settings()

func set_invert_yaw(val: bool) -> void:
	invert_yaw = val
	save_settings()

func reset_sensitivity_defaults() -> void:
	sensitivity_overall = 1.0
	sensitivity_yaw = 1.0
	sensitivity_pitch = 1.0
	sensitivity_roll = 1.0
	invert_pitch = false
	invert_yaw = false
	save_settings()

func save_settings() -> void:
	var cfg = ConfigFile.new()
	cfg.set_value("sensitivity", "overall", sensitivity_overall)
	cfg.set_value("sensitivity", "yaw", sensitivity_yaw)
	cfg.set_value("sensitivity", "pitch", sensitivity_pitch)
	cfg.set_value("sensitivity", "roll", sensitivity_roll)
	cfg.set_value("controls", "invert_pitch", invert_pitch)
	cfg.set_value("controls", "invert_yaw", invert_yaw)
	cfg.save(SETTINGS_FILE_PATH)

func load_settings() -> void:
	var cfg = ConfigFile.new()
	var err = cfg.load(SETTINGS_FILE_PATH)
	if err == OK:
		sensitivity_overall = cfg.get_value("sensitivity", "overall", 1.0)
		sensitivity_yaw = cfg.get_value("sensitivity", "yaw", 1.0)
		sensitivity_pitch = cfg.get_value("sensitivity", "pitch", 1.0)
		sensitivity_roll = cfg.get_value("sensitivity", "roll", 1.0)
		invert_pitch = cfg.get_value("controls", "invert_pitch", false)
		invert_yaw = cfg.get_value("controls", "invert_yaw", false)

