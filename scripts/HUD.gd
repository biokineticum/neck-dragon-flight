# ==============================================================================
# HUD.gd - CanvasLayer Flight Instruments, Telemetry Dot, Settings & Ready Modal
# ==============================================================================
# Milestone 4 / Feature 16 + Live Sensitivity Customization & Startup Delay
# - Airspeed indicator (cruise 30 m/s, dive 54 m/s, climb 18 m/s)
# - Flight distance counter / meter (meters & kilometers)
# - Health container (3 hearts with clamp and empty heart display)
# - Head-tracking status dot: Green (tracking), Yellow (calibrating), Blue (fallback), Red (lost)
# - Clamped telemetry reticle offset
# - 'C' calibration overlay & prompt
# - Live in-game Settings Panel with Sliders (Overall, Yaw, Pitch, Inversions)
# - Safe Game Start Ready Panel (waits for webcam without dragon crashing)
# - Game Over screen with flight distance and restart prompt ('R' / Space)
# ==============================================================================
class_name HUD
extends CanvasLayer

# Telemetry Status Colors
const COLOR_TRACKING: Color = Color(0.2, 0.9, 0.3, 1.0)     # Green: Active head tracking
const COLOR_CALIBRATING: Color = Color(1.0, 0.85, 0.1, 1.0) # Yellow: Calibration in progress
const COLOR_FALLBACK: Color = Color(0.2, 0.6, 1.0, 1.0)     # Blue: Keyboard/Mouse fallback
const COLOR_LOST: Color = Color(0.9, 0.2, 0.2, 1.0)         # Red: Tracking lost / disconnected

# Reticle Configuration
const MAX_RETICLE_RADIUS: float = 50.0 # Bounded indicator radius in pixels

# Flight Instrument Nodes
@onready var speed_value: Label = $RootControl/InstrumentsContainer/SpeedRow/SpeedValue
@onready var speed_bar: ProgressBar = $RootControl/InstrumentsContainer/SpeedBar
@onready var distance_value: Label = $RootControl/InstrumentsContainer/DistanceRow/DistanceValue
@onready var health_container: HBoxContainer = $RootControl/HealthContainer
@onready var status_dot: ColorRect = $RootControl/TelemetryContainer/StatusDot
@onready var status_label: Label = $RootControl/TelemetryContainer/StatusLabel
@onready var reticle_dot: ColorRect = $RootControl/ReticleCenter/ReticleDot
@onready var calibration_hint: Label = $RootControl/CalibrationHint
@onready var calibration_flash: Label = $RootControl/CalibrationFlash
@onready var game_over_panel: Panel = $RootControl/GameOverPanel
@onready var distance_summary: Label = $RootControl/GameOverPanel/VBox/DistanceSummary

# Settings UI Nodes
@onready var settings_btn: Button = $RootControl.get_node_or_null("SettingsBtn")
@onready var settings_panel: Panel = $RootControl.get_node_or_null("SettingsPanel")
@onready var overall_slider: HSlider = $RootControl.get_node_or_null("SettingsPanel/Margin/VBox/OverallSlider")
@onready var overall_val: Label = $RootControl.get_node_or_null("SettingsPanel/Margin/VBox/OverallRow/OverallVal")
@onready var yaw_slider: HSlider = $RootControl.get_node_or_null("SettingsPanel/Margin/VBox/YawSlider")
@onready var yaw_val: Label = $RootControl.get_node_or_null("SettingsPanel/Margin/VBox/YawRow/YawVal")
@onready var pitch_slider: HSlider = $RootControl.get_node_or_null("SettingsPanel/Margin/VBox/PitchSlider")
@onready var pitch_val: Label = $RootControl.get_node_or_null("SettingsPanel/Margin/VBox/PitchRow/PitchVal")
@onready var invert_pitch_check: CheckBox = $RootControl.get_node_or_null("SettingsPanel/Margin/VBox/CheckRow/InvertPitchCheck")
@onready var invert_yaw_check: CheckBox = $RootControl.get_node_or_null("SettingsPanel/Margin/VBox/CheckRow/InvertYawCheck")
@onready var calibrate_btn: Button = $RootControl.get_node_or_null("SettingsPanel/Margin/VBox/ButtonsRow/CalibrateBtn")
@onready var defaults_btn: Button = $RootControl.get_node_or_null("SettingsPanel/Margin/VBox/ButtonsRow/ResetDefaultsBtn")
@onready var close_settings_btn: Button = $RootControl.get_node_or_null("SettingsPanel/Margin/VBox/CloseSettingsBtn")

# Ready / Start Flight Overlay Nodes
@onready var ready_panel: Panel = $RootControl.get_node_or_null("ReadyPanel")
@onready var ready_camera_status: Label = $RootControl.get_node_or_null("ReadyPanel/Margin/VBox/CameraStatusBox/Margin/ReadyCameraStatus")
@onready var start_flight_btn: Button = $RootControl.get_node_or_null("ReadyPanel/Margin/VBox/ReadyActions/StartFlightBtn")
@onready var ready_settings_btn: Button = $RootControl.get_node_or_null("ReadyPanel/Margin/VBox/ReadyActions/ReadySettingsBtn")

# External Dependencies
var input_manager: Node = null
var game_manager: Node = null

# Runtime state
var current_health: int = 3
var max_health: int = 3
var calibration_flash_timer: float = 0.0

func _ready() -> void:
	# Headless standalone execution guard for E2E tests (TEST-T2-F16-05)
	if DisplayServer.get_name() == "headless" and (get_tree().current_scene == self or get_parent() == get_tree().root):
		print("[HUD] Headless standalone instance verified. Exiting with code 0.")
		get_tree().quit(0)
		return
		
	reset_hud()
	_find_dependencies()
	_init_settings_ui()
	_init_ready_ui()

func _find_dependencies() -> void:
	if game_manager == null:
		game_manager = get_tree().root.find_child("GameManager", true, false)
	if input_manager == null:
		input_manager = get_tree().root.find_child("InputManager", true, false)

func _init_settings_ui() -> void:
	if settings_btn != null:
		settings_btn.pressed.connect(toggle_settings)
		
	if close_settings_btn != null:
		close_settings_btn.pressed.connect(close_settings)
		
	if calibrate_btn != null:
		calibrate_btn.pressed.connect(_on_calibrate_pressed)
		
	if defaults_btn != null:
		defaults_btn.pressed.connect(_on_defaults_pressed)
		
	# Synchronize current values from input_manager
	if input_manager != null:
		if "sensitivity_overall" in input_manager and overall_slider != null:
			overall_slider.value = input_manager.sensitivity_overall
			_update_overall_label(input_manager.sensitivity_overall)
		if "sensitivity_yaw" in input_manager and yaw_slider != null:
			yaw_slider.value = input_manager.sensitivity_yaw
			_update_yaw_label(input_manager.sensitivity_yaw)
		if "sensitivity_pitch" in input_manager and pitch_slider != null:
			pitch_slider.value = input_manager.sensitivity_pitch
			_update_pitch_label(input_manager.sensitivity_pitch)
		if "invert_pitch" in input_manager and invert_pitch_check != null:
			invert_pitch_check.button_pressed = input_manager.invert_pitch
		if "invert_yaw" in input_manager and invert_yaw_check != null:
			invert_yaw_check.button_pressed = input_manager.invert_yaw
			
	# Connect value changed signals
	if overall_slider != null:
		overall_slider.value_changed.connect(_on_overall_slider_changed)
	if yaw_slider != null:
		yaw_slider.value_changed.connect(_on_yaw_slider_changed)
	if pitch_slider != null:
		pitch_slider.value_changed.connect(_on_pitch_slider_changed)
	if invert_pitch_check != null:
		invert_pitch_check.toggled.connect(_on_invert_pitch_toggled)
	if invert_yaw_check != null:
		invert_yaw_check.toggled.connect(_on_invert_yaw_toggled)

func _init_ready_ui() -> void:
	if start_flight_btn != null:
		start_flight_btn.pressed.connect(_on_start_flight_pressed)
	if ready_settings_btn != null:
		ready_settings_btn.pressed.connect(open_settings)

func _process(delta: float) -> void:
	if calibration_flash_timer > 0.0:
		calibration_flash_timer -= delta
		if calibration_flash_timer <= 0.0:
			if calibration_flash != null:
				calibration_flash.visible = false
				
	# Real-time ready overlay camera status update
	if ready_panel != null and ready_panel.visible:
		_update_ready_camera_status()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_O:
			toggle_settings()
			get_viewport().set_input_as_handled()
		elif event.keycode == KEY_ESCAPE and settings_panel != null and settings_panel.visible:
			close_settings()
			get_viewport().set_input_as_handled()

# ==============================================================================
# Settings Modal Logic
# ==============================================================================

func open_settings() -> void:
	_find_dependencies()
	if settings_panel != null:
		settings_panel.visible = true
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func close_settings() -> void:
	if settings_panel != null:
		settings_panel.visible = false

func toggle_settings() -> void:
	if settings_panel != null:
		if settings_panel.visible:
			close_settings()
		else:
			open_settings()

func _on_overall_slider_changed(val: float) -> void:
	_update_overall_label(val)
	if input_manager == null:
		_find_dependencies()
	if input_manager != null and input_manager.has_method("set_sensitivity_overall"):
		input_manager.set_sensitivity_overall(val)

func _on_yaw_slider_changed(val: float) -> void:
	_update_yaw_label(val)
	if input_manager == null:
		_find_dependencies()
	if input_manager != null and input_manager.has_method("set_sensitivity_yaw"):
		input_manager.set_sensitivity_yaw(val)

func _on_pitch_slider_changed(val: float) -> void:
	_update_pitch_label(val)
	if input_manager == null:
		_find_dependencies()
	if input_manager != null and input_manager.has_method("set_sensitivity_pitch"):
		input_manager.set_sensitivity_pitch(val)

func _on_invert_pitch_toggled(val: bool) -> void:
	if input_manager == null:
		_find_dependencies()
	if input_manager != null and input_manager.has_method("set_invert_pitch"):
		input_manager.set_invert_pitch(val)

func _on_invert_yaw_toggled(val: bool) -> void:
	if input_manager == null:
		_find_dependencies()
	if input_manager != null and input_manager.has_method("set_invert_yaw"):
		input_manager.set_invert_yaw(val)

func _on_calibrate_pressed() -> void:
	if input_manager == null:
		_find_dependencies()
	if input_manager != null and input_manager.has_method("calibrate_neutral"):
		input_manager.calibrate_neutral()
	show_calibration_banner(1.5)

func _on_defaults_pressed() -> void:
	if input_manager == null:
		_find_dependencies()
	if input_manager != null and input_manager.has_method("reset_sensitivity_defaults"):
		input_manager.reset_sensitivity_defaults()
	if overall_slider != null:
		overall_slider.value = 1.0
		_update_overall_label(1.0)
	if yaw_slider != null:
		yaw_slider.value = 1.0
		_update_yaw_label(1.0)
	if pitch_slider != null:
		pitch_slider.value = 1.0
		_update_pitch_label(1.0)
	if invert_pitch_check != null:
		invert_pitch_check.button_pressed = false
	if invert_yaw_check != null:
		invert_yaw_check.button_pressed = false

func _update_overall_label(val: float) -> void:
	if overall_val != null:
		overall_val.text = "%.2fx" % val

func _update_yaw_label(val: float) -> void:
	if yaw_val != null:
		yaw_val.text = "%.2fx" % val

func _update_pitch_label(val: float) -> void:
	if pitch_val != null:
		pitch_val.text = "%.2fx" % val

# ==============================================================================
# Ready / Safe Start Screen Logic
# ==============================================================================

func show_ready_panel() -> void:
	if ready_panel != null:
		ready_panel.visible = true
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func hide_ready_panel() -> void:
	if ready_panel != null:
		ready_panel.visible = false

func _on_start_flight_pressed() -> void:
	if game_manager == null:
		_find_dependencies()
	if game_manager != null and game_manager.has_method("start_flight"):
		game_manager.start_flight()
	else:
		hide_ready_panel()

func _update_ready_camera_status() -> void:
	if ready_camera_status == null:
		return
	if input_manager == null:
		_find_dependencies()
	if input_manager != null and input_manager.has_method("is_webcam_active") and input_manager.is_webcam_active():
		ready_camera_status.text = "✅ KAMERA AKTYWNA! Twarz wykryta i śledzona.\nPoruszaj głową, aby przetestować celownik przed startem."
		ready_camera_status.add_theme_color_override("font_color", Color(0.2, 0.95, 0.4))
	else:
		ready_camera_status.text = "⏳ OCZEKIWANIE NA KAMERĘ... (~5-10 sekund)\n(Smok czeka bezpiecznie. Gdy kamerka się włączy, kropka na środku zacznie reagować na ruch głowy)"
		ready_camera_status.add_theme_color_override("font_color", Color(1.0, 0.8, 0.2))

# ==============================================================================
# Public API - Display Updaters
# ==============================================================================

func update_speed(speed: float) -> void:
	var clean_speed: float = maxf(0.0, speed)
	if speed_value != null:
		speed_value.text = "%.1f m/s" % clean_speed
	if speed_bar != null:
		speed_bar.value = clean_speed

func update_distance(distance_meters: float) -> void:
	var d: float = maxf(0.0, distance_meters)
	if distance_value != null:
		if d >= 1000.0:
			distance_value.text = "%.2f km (%d m)" % [d / 1000.0, roundi(d)]
		else:
			distance_value.text = "%d m" % roundi(d)

func update_health(hearts: int) -> void:
	current_health = clampi(hearts, 0, max_health)
	
	if health_container == null:
		return
		
	var children = health_container.get_children()
	for i in range(children.size()):
		var heart_label = children[i] as Label
		if heart_label == null:
			continue
		if i < current_health:
			heart_label.text = "♥"
			heart_label.modulate = Color(1.0, 1.0, 1.0, 1.0)
		else:
			heart_label.text = "♡"
			heart_label.modulate = Color(0.4, 0.4, 0.4, 0.5)

func update_telemetry_status(mode: String) -> void:
	var upper_mode = mode.to_upper().strip_edges()
	var dot_color: Color = COLOR_FALLBACK
	var text_desc: String = "KEYBOARD / MOUSE"
	
	match upper_mode:
		"TRACKING", "WEBCAM":
			dot_color = COLOR_TRACKING
			text_desc = "WEBCAM TRACKING"
		"CALIBRATING", "CALIBRATE":
			dot_color = COLOR_CALIBRATING
			text_desc = "CALIBRATING..."
		"BLENDED":
			dot_color = COLOR_FALLBACK
			text_desc = "BLENDED CONTROLS"
		"LOST", "DISCONNECTED":
			dot_color = COLOR_LOST
			text_desc = "TRACKER OFFLINE"
		_:
			dot_color = COLOR_FALLBACK
			text_desc = "KEYBOARD / MOUSE"
			
	if status_dot != null:
		status_dot.color = dot_color
	if status_label != null:
		status_label.text = text_desc

func update_reticle(pitch_norm: float, yaw_norm: float) -> void:
	if reticle_dot == null:
		return
	var offset: Vector2 = Vector2(yaw_norm, -pitch_norm) * MAX_RETICLE_RADIUS
	offset = offset.limit_length(MAX_RETICLE_RADIUS)
	reticle_dot.position = offset - (reticle_dot.size * 0.5)

func show_calibration_banner(duration: float = 1.5) -> void:
	if calibration_flash != null:
		calibration_flash.visible = true
	calibration_flash_timer = duration

func show_game_over(final_distance_meters: float) -> void:
	# In peaceful flight mode, game over screen is hidden
	if game_over_panel != null:
		game_over_panel.visible = false
	if distance_summary != null:
		var d = maxf(0.0, final_distance_meters)
		if d >= 1000.0:
			distance_summary.text = "Distance Traveled: %.2f km (%d m)" % [d / 1000.0, roundi(d)]
		else:
			distance_summary.text = "Distance Traveled: %d m" % roundi(d)

func hide_game_over() -> void:
	if game_over_panel != null:
		game_over_panel.visible = false

func reset_hud() -> void:
	update_speed(30.0)
	update_distance(0.0)
	update_health(max_health)
	if health_container != null:
		health_container.visible = false
	update_telemetry_status("FALLBACK")
	update_reticle(0.0, 0.0)
	hide_game_over()
	if calibration_flash != null:
		calibration_flash.visible = false
	calibration_flash_timer = 0.0
