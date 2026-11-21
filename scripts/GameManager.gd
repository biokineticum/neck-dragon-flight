# ==============================================================================
# GameManager.gd - Master Game Loop, State Machine & Reset Coordinator
# ==============================================================================
# Milestone 4 / Feature 15:
# - State machine: READY -> FLYING -> CRASHING -> GAME_OVER
# - Collision damage & invulnerability frames (Feature 14)
# - Hit-stop time dilation (0.20s at Engine.time_scale = 0.05)
# - Camera trauma shake triggering (1.0 on fatal crash, 0.5 on glancing)
# - Accumulated forward flight distance tracking
# - Deterministic, idempotent reset loop ('R' key or reset_game())
# ==============================================================================
class_name GameManager
extends Node

# State enum definition
enum GameState {
	READY,
	FLYING,
	CRASHING,
	GAME_OVER
}

# State change signals
signal state_changed(new_state: GameState, old_state: GameState)
signal health_changed(current_health: int, max_health: int)
signal game_restarted()

# Configuration constants
const MAX_HEALTH: int = 3
const HIT_STOP_DURATION: float = 0.20        # 0.20s real-world hit-stop duration
const HIT_STOP_TIME_SCALE: float = 0.05      # Extreme slow motion during impact
const INVULNERABILITY_TIME: float = 1.0      # Post-collision immunity window (TEST-T1-F14-05)
const START_POSITION: Vector3 = Vector3(0, 25, 0)
const CRUISE_SPEED: float = 30.0

# Node references
@export var player_dragon_path: NodePath = NodePath("../PlayerDragon")
@export var chunk_manager_path: NodePath = NodePath("../ChunkManager")
@export var hud_path: NodePath = NodePath("../HUD")
@export var start_in_flying_state: bool = false
@export var peaceful_mode: bool = true

# Runtime state
var current_state: GameState = GameState.FLYING
var current_health: int = MAX_HEALTH
var player_health: int = MAX_HEALTH  # Alias for test contract compatibility (TEST-T1-F14-04)
var total_distance: float = 0.0

var is_invulnerable: bool = false
var invulnerability_timer: float = 0.0

var is_in_hit_stop: bool = false
var hit_stop_timer: float = 0.0
var hit_stop_end_msec: int = 0
var hit_stop_session: int = 0

# Resolved node references
var player_dragon: CharacterBody3D = null
var flight_controller: Node = null
var input_manager: Node = null
var camera_rig: Node = null
var chunk_manager: Node = null
var hud: CanvasLayer = null

func _ready() -> void:
	_resolve_node_references()
	_wire_signals()
	if not get_tree().process_frame.is_connected(_check_hit_stop):
		get_tree().process_frame.connect(_check_hit_stop)
	if start_in_flying_state:
		reset_game(GameState.FLYING)
	else:
		reset_game(GameState.READY)

func _exit_tree() -> void:
	if get_tree() != null and get_tree().process_frame.is_connected(_check_hit_stop):
		get_tree().process_frame.disconnect(_check_hit_stop)

func _resolve_node_references() -> void:
	if has_node(player_dragon_path):
		player_dragon = get_node(player_dragon_path) as CharacterBody3D
	elif get_tree().root.find_child("PlayerDragon", true, false) != null:
		player_dragon = get_tree().root.find_child("PlayerDragon", true, false) as CharacterBody3D
		
	if player_dragon != null:
		flight_controller = player_dragon.find_child("FlightController", true, false)
		input_manager = player_dragon.find_child("InputManager", true, false)
		camera_rig = player_dragon.find_child("CameraRig", true, false)
		
	if has_node(chunk_manager_path):
		chunk_manager = get_node(chunk_manager_path)
	elif get_tree().root.find_child("ChunkManager", true, false) != null:
		chunk_manager = get_tree().root.find_child("ChunkManager", true, false)
		
	if has_node(hud_path):
		hud = get_node(hud_path) as CanvasLayer
	elif get_tree().root.find_child("HUD", true, false) != null:
		hud = get_tree().root.find_child("HUD", true, false) as CanvasLayer

func _wire_signals() -> void:
	if flight_controller != null:
		if not flight_controller.speed_changed.is_connected(_on_speed_changed):
			flight_controller.speed_changed.connect(_on_speed_changed)
		if not flight_controller.distance_updated.is_connected(_on_distance_updated):
			flight_controller.distance_updated.connect(_on_distance_updated)
		if not flight_controller.collision_impact.is_connected(_on_collision_impact):
			flight_controller.collision_impact.connect(_on_collision_impact)
			
	if chunk_manager != null and player_dragon != null:
		chunk_manager.player_ref = player_dragon

func _check_hit_stop() -> void:
	if is_in_hit_stop:
		var remaining_msec = hit_stop_end_msec - Time.get_ticks_msec()
		if remaining_msec <= 0:
			_end_hit_stop()

func _process(delta: float) -> void:
	# Update hit-stop in unscaled wall-clock time
	_check_hit_stop()
			
	# Update invulnerability timer
	if is_invulnerable:
		invulnerability_timer -= delta
		if invulnerability_timer <= 0.0:
			is_invulnerable = false
			invulnerability_timer = 0.0
			
	# Forward telemetry status to HUD
	_update_hud_telemetry()

func _unhandled_input(event: InputEvent) -> void:
	# Restart key 'R' (TEST-T1-F15-05, TEST-T2-F15-03)
	if event.is_action_pressed("restart"):
		reset_game(GameState.READY)
		return
		
	# Space or Enter starts game from READY state
	if current_state == GameState.READY:
		if event is InputEventKey and event.pressed and not event.echo:
			if event.keycode == KEY_SPACE or event.keycode == KEY_ENTER:
				start_flight()
	elif current_state == GameState.GAME_OVER:
		if event is InputEventKey and event.pressed and (event.keycode == KEY_SPACE or event.keycode == KEY_R):
			reset_game(GameState.READY)

func start_flight() -> void:
	if current_state == GameState.READY:
		change_state(GameState.FLYING)
		if flight_controller != null:
			flight_controller.set_flight_enabled(true)
		if hud != null and hud.has_method("hide_ready_panel"):
			hud.hide_ready_panel()

func change_state(new_state: GameState) -> void:
	if current_state == new_state:
		return
	var old_state = current_state
	current_state = new_state
	state_changed.emit(new_state, old_state)

func _on_collision_impact(_collider: Node, _collision_point: Vector3, _normal: Vector3) -> void:
	if current_state != GameState.FLYING:
		return
	if peaceful_mode:
		# Milestone M1 / Requirement R2: Peaceful Open-World Flight
		# Terrain and obstacle contact causes no damage, health loss, camera crash trauma,
		# hit-stop freezes, or game over states. Flight is continuous and peaceful.
		return
		
	if is_invulnerable:
		return
		
	# Decrement health by exactly 1 (TEST-T1-F14-04)
	current_health -= 1
	player_health = current_health
	health_changed.emit(current_health, MAX_HEALTH)
	if hud != null and hud.has_method("update_health"):
		hud.update_health(current_health)
		
	if current_health <= 0:
		_trigger_crash()
	else:
		_trigger_glancing_hit()

func _trigger_glancing_hit() -> void:
	is_invulnerable = true
	invulnerability_timer = INVULNERABILITY_TIME
	if camera_rig != null and camera_rig.has_method("add_trauma"):
		camera_rig.add_trauma(0.5)

func _trigger_crash() -> void:
	change_state(GameState.CRASHING)
	
	# Fatal collision sets camera trauma to maximum 1.0 (TEST-T1-F15-02)
	if camera_rig != null and camera_rig.has_method("add_trauma"):
		camera_rig.add_trauma(1.0)
	elif camera_rig != null and "trauma" in camera_rig:
		camera_rig.trauma = 1.0
		
	# Dilate Engine.time_scale to 0.05 for 0.20s hit-stop window (TEST-T1-F15-01, TEST-T2-F15-01)
	Engine.time_scale = 0.05
	is_in_hit_stop = true
	hit_stop_timer = 0.20
	hit_stop_session += 1
	var session = hit_stop_session
	hit_stop_end_msec = Time.get_ticks_msec() + int(HIT_STOP_DURATION * 1000.0)
	
	# Unscaled timer backup (TEST-T2-F15-01)
	get_tree().create_timer(0.225, true, false, true).timeout.connect(func():
		if is_in_hit_stop and hit_stop_session == session:
			_end_hit_stop()
	)

func _end_hit_stop() -> void:
	if not is_in_hit_stop:
		return
	is_in_hit_stop = false
	hit_stop_timer = 0.0
	hit_stop_end_msec = 0
	Engine.time_scale = 1.0
	
	if current_state == GameState.CRASHING:
		change_state(GameState.GAME_OVER)
		if flight_controller != null:
			flight_controller.set_flight_enabled(false)
		if hud != null:
			if hud.has_method("show_game_over"):
				hud.show_game_over(total_distance)
			elif "visible" in hud:
				hud.visible = true

func reset_game(target_state: GameState = GameState.FLYING) -> void:
	# 1. Restore time scale immediately (TEST-T2-F15-02)
	Engine.time_scale = 1.0
	is_in_hit_stop = false
	hit_stop_timer = 0.0
	hit_stop_end_msec = 0
	hit_stop_session += 1
	
	# 2. Reset health and invulnerability
	current_health = MAX_HEALTH
	player_health = MAX_HEALTH
	is_invulnerable = false
	invulnerability_timer = 0.0
	
	# 3. Reset distance
	total_distance = 0.0
	
	# 4. Reset FlightController state (position, velocity, attitude)
	if flight_controller != null:
		flight_controller.reset_flight_state(START_POSITION)
		flight_controller.set_flight_enabled(target_state == GameState.FLYING)
	elif player_dragon != null:
		player_dragon.global_position = START_POSITION
		player_dragon.velocity = Vector3(0, 0, -CRUISE_SPEED)
		
	# 5. Reset ChunkManager corridor chunks (TEST-T2-F15-05)
	if chunk_manager != null:
		if chunk_manager.has_method("reset_chunks"):
			chunk_manager.reset_chunks()
		elif chunk_manager.has_method("reset_corridor"):
			chunk_manager.reset_corridor()
			
	# 6. Reset CameraRig trauma & transforms
	if camera_rig != null:
		if camera_rig.has_method("reset_camera"):
			camera_rig.reset_camera()
		if "trauma" in camera_rig:
			camera_rig.trauma = 0.0
			
	# 7. Reset HUD
	if hud != null:
		if hud.has_method("hide_game_over"):
			hud.hide_game_over()
		if hud.has_method("update_health"):
			hud.update_health(current_health)
		if hud.has_method("update_distance"):
			hud.update_distance(0.0)
		if hud.has_method("update_speed"):
			hud.update_speed(0.0 if target_state == GameState.READY else CRUISE_SPEED)
		if target_state == GameState.READY and hud.has_method("show_ready_panel"):
			hud.show_ready_panel()
		elif target_state == GameState.FLYING and hud.has_method("hide_ready_panel"):
			hud.hide_ready_panel()
			
	# 8. Set state
	change_state(target_state)
	game_restarted.emit()

func _on_speed_changed(speed: float, _min_s: float, _max_s: float) -> void:
	if hud != null and hud.has_method("update_speed"):
		hud.update_speed(speed)

func _on_distance_updated(dist: float) -> void:
	total_distance = dist
	if hud != null and hud.has_method("update_distance"):
		hud.update_distance(total_distance)

func _update_hud_telemetry() -> void:
	if hud == null or not hud.has_method("update_telemetry_status"):
		return
	if input_manager == null:
		hud.update_telemetry_status("KEYBOARD_MOUSE")
		return
	if input_manager.is_webcam_active():
		hud.update_telemetry_status("TRACKING")
	else:
		hud.update_telemetry_status(input_manager.get_control_mode())

# Public getters for testing
func get_state() -> GameState:
	return current_state

func get_state_name() -> String:
	match current_state:
		GameState.READY: return "READY"
		GameState.FLYING: return "FLYING"
		GameState.CRASHING: return "CRASHING"
		GameState.GAME_OVER: return "GAME_OVER"
		_: return "UNKNOWN"

func get_health() -> int:
	return current_health

func get_distance() -> float:
	return total_distance
