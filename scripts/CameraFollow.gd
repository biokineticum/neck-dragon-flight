# ==============================================================================
# CameraFollow.gd - Dual-Tier Spring-Damped Rider Camera Rig & Roll Lag
# ==============================================================================
# Milestone 3 / Requirement R1, Acceptance Criteria F12:
# - Rider saddle mount at Vector3(0.0, 1.4, -0.2)
# - Roll lag ratio: 0.65 (camera world roll = 0.65 * dragon roll)
# - Dynamic speed FOV: 75.0° (cruise) to 90.0° (dive)
# - Harmonic wing flap bobbing coupling (amplitude <= 0.05m)
# - Instant teleport snap on reset
# ==============================================================================
class_name CameraFollow
extends Node3D

const CAMERA_LOCAL_POS: Vector3 = Vector3(0.0, 1.4, -0.2)
const BASE_FOV: float = 75.0
const MAX_FOV: float = 90.0
const ROLL_LAG_RATIO: float = 0.65

@export var target_path: NodePath = NodePath("..")
@export var camera_path: NodePath = NodePath("Camera3D")
@export var flight_controller_path: NodePath = NodePath("../FlightController")
@export var visual_rig_path: NodePath = NodePath("../DragonVisualRig")

# Damping and interpolation constants
@export var roll_lag_ratio: float = 0.65
@export var roll_smoothing_lambda: float = 10.5 # Produces ~0.65 lag ratio at 100ms
@export var fov_lerp_speed: float = 8.0
@export var heave_coupling_amplitude: float = 0.03 # <= 0.05m bobbing

var target: Node3D = null
var camera_node: Camera3D = null
var flight_controller: Node = null
var visual_rig: Node = null

var smoothed_roll: float = 0.0
var current_camera_roll_deg: float = 0.0

# Trauma camera shake properties (Feature 14/15)
@export var trauma_decay_rate: float = 1.2
var trauma: float = 0.0
var shake_offset: Vector3 = Vector3.ZERO
var shake_rotation: Vector3 = Vector3.ZERO

const MAX_SHAKE_TRANSLATION: Vector3 = Vector3(0.35, 0.25, 0.20)
const MAX_SHAKE_ROTATION_DEG: Vector3 = Vector3(4.0, 4.0, 6.0)

func _ready() -> void:
	position = CAMERA_LOCAL_POS
	
	if has_node(target_path):
		target = get_node(target_path) as Node3D
	elif get_parent() is Node3D:
		target = get_parent() as Node3D
		
	if has_node(camera_path):
		camera_node = get_node(camera_path) as Camera3D
	else:
		camera_node = _find_or_create_camera()
		
	if has_node(flight_controller_path):
		flight_controller = get_node(flight_controller_path)
		
	if has_node(visual_rig_path):
		visual_rig = get_node(visual_rig_path)
		
	reset_camera()

func _find_or_create_camera() -> Camera3D:
	for child in get_children():
		if child is Camera3D:
			return child
	var cam = Camera3D.new()
	cam.name = "Camera3D"
	cam.fov = BASE_FOV
	cam.near = 0.05
	cam.far = 3500.0
	cam.current = true
	add_child(cam)
	return cam

func _process(delta: float) -> void:
	if delta <= 0.0:
		return
		
	# 1. Fetch flight speed and dragon body roll
	var speed: float = 30.0
	var dragon_roll_deg: float = 0.0
	
	if flight_controller != null:
		if flight_controller.has_method("get_current_speed"):
			speed = flight_controller.get_current_speed()
		elif "current_speed" in flight_controller:
			speed = flight_controller.current_speed
			
		if flight_controller.has_method("get_roll_degrees"):
			dragon_roll_deg = flight_controller.get_roll_degrees()
		elif "current_roll" in flight_controller:
			dragon_roll_deg = rad_to_deg(flight_controller.current_roll)
			
	# 2. Dynamic Speed FOV Expansion [75.0°, 90.0°]
	_update_dynamic_fov(speed, delta)
	
	# 3. Dynamic Roll Lag Ratio (0.65)
	_update_roll_lag(dragon_roll_deg, delta)
	
	# 4. Harmonic Flap Bobbing Coupling (<= 0.05m)
	_update_flap_bobbing()
	
	# 5. Trauma Camera Shake Decay & Application
	_update_trauma_shake(delta)

func _update_dynamic_fov(speed: float, delta: float) -> void:
	if camera_node == null:
		return
	var speed_ratio: float = clampf((speed - 30.0) / (54.0 - 30.0), 0.0, 1.0)
	var target_fov: float = lerpf(BASE_FOV, MAX_FOV, speed_ratio)
	camera_node.fov = clampf(lerpf(camera_node.fov, target_fov, 1.0 - exp(-maxf(fov_lerp_speed, 0.0) * delta)), 74.0, 92.0)

func _update_roll_lag(dragon_roll_deg: float, delta: float) -> void:
	# Target world roll
	var target_world_roll: float = dragon_roll_deg * roll_lag_ratio
	smoothed_roll = lerpf(smoothed_roll, target_world_roll, 1.0 - exp(-roll_smoothing_lambda * delta))
	current_camera_roll_deg = smoothed_roll
	
	# Local counter-rotation relative to dragon parent
	# Since parent rolls by dragon_roll_deg around -Z, local roll must be smoothed_roll - dragon_roll_deg
	var local_roll_deg: float = smoothed_roll - dragon_roll_deg
	transform.basis = Basis().rotated(Vector3(0, 0, -1), deg_to_rad(local_roll_deg))

func _update_flap_bobbing() -> void:
	var bob_y: float = 0.0
	if visual_rig != null and "flap_phase" in visual_rig:
		var phase: float = visual_rig.flap_phase
		bob_y = sin(phase) * heave_coupling_amplitude
	position = CAMERA_LOCAL_POS + Vector3(0.0, bob_y, 0.0)

func reset_camera() -> void:
	position = CAMERA_LOCAL_POS
	transform.basis = Basis()
	smoothed_roll = 0.0
	current_camera_roll_deg = 0.0
	trauma = 0.0
	shake_offset = Vector3.ZERO
	shake_rotation = Vector3.ZERO
	if camera_node != null:
		camera_node.fov = BASE_FOV
		camera_node.near = 0.05
		camera_node.position = Vector3.ZERO
		camera_node.rotation = Vector3.ZERO

func add_trauma(amount: float) -> void:
	trauma = clampf(trauma + amount, 0.0, 1.0)

func get_trauma() -> float:
	return trauma

func get_shake_offset() -> Vector3:
	return shake_offset

func _update_trauma_shake(delta: float) -> void:
	if trauma > 0.0:
		trauma = maxf(0.0, trauma - trauma_decay_rate * delta)
		var shake = trauma * trauma
		var time_val = Time.get_ticks_msec() * 0.035
		var nx = sin(time_val * 1.7)
		var ny = cos(time_val * 2.3)
		var nz = sin(time_val * 2.9)
		var nr_pitch = cos(time_val * 1.9)
		var nr_yaw = sin(time_val * 2.1)
		var nr_roll = cos(time_val * 2.7)
		
		shake_offset = Vector3(
			MAX_SHAKE_TRANSLATION.x * nx * shake,
			MAX_SHAKE_TRANSLATION.y * ny * shake,
			MAX_SHAKE_TRANSLATION.z * nz * shake
		)
		shake_rotation = Vector3(
			deg_to_rad(MAX_SHAKE_ROTATION_DEG.x * nr_pitch * shake),
			deg_to_rad(MAX_SHAKE_ROTATION_DEG.y * nr_yaw * shake),
			deg_to_rad(MAX_SHAKE_ROTATION_DEG.z * nr_roll * shake)
		)
	else:
		shake_offset = Vector3.ZERO
		shake_rotation = Vector3.ZERO
		
	if camera_node != null:
		camera_node.position = shake_offset
		camera_node.rotation = shake_rotation

func get_camera_roll() -> float:
	return current_camera_roll_deg

func get_camera_fov() -> float:
	return camera_node.fov if camera_node != null else BASE_FOV
