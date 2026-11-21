# ==============================================================================
# FlightController.gd - Flight Aerodynamics & Banking Kinematics Engine
# ==============================================================================
# Milestone 3 / Requirements R1, R2, Acceptance Criteria F10, F11:
# - Continuous forward flight along -Z basis vector
# - Cruise speed: 30.0 m/s, dive max: 54.0 m/s, climb stall floor: 18.0 m/s
# - Coordinated banking turns: pitch [-32°, +32°], yaw 38°/s, roll [-42°, +42°]
# - Signals: speed_changed, altitude_changed, distance_updated, collision_impact
# - Anti-drift orthonormal basis preservation (det ~ 1.0)
# ==============================================================================
class_name FlightController
extends Node

const ProceduralMeshGen = preload("res://scripts/ProceduralMeshGen.gd")

# Signal contracts (Interface Contract 3)
signal speed_changed(current_speed: float, min_speed: float, max_speed: float)
signal altitude_changed(current_altitude: float)
signal distance_updated(distance_meters: float)
signal collision_impact(collider: Node, collision_point: Vector3, normal: Vector3)

# Aerodynamic physical constants (matching config.py & TEST_INFRA.md)
const CRUISE_SPEED: float = 30.0
const MAX_DIVE_SPEED: float = 54.0
const MIN_CLIMB_SPEED: float = 18.0

const ACCELERATION_DIVE: float = 12.0
const DECELERATION_CLIMB: float = 8.0
const DRAG_DECELERATION: float = 4.0

const MAX_PITCH_DEG: float = 32.0
const MAX_YAW_RATE_DPS: float = 38.0
const MAX_BANK_ANGLE_DEG: float = 42.0

# Node references
@export var body_path: NodePath = NodePath("..")
@export var input_manager_path: NodePath = NodePath("../InputManager")
@export var camera_rig_path: NodePath = NodePath("../CameraRig")
@export var visual_rig_path: NodePath = NodePath("../DragonVisualRig")

# Configurable parameters
@export var min_speed: float = 18.0
@export var flight_enabled: bool = true
@export var pitch_response_speed: float = 16.0
@export var roll_response_speed: float = 14.0

# Runtime flight state
var body: CharacterBody3D = null
var input_manager: Node = null
var camera_rig: Node = null
var visual_rig: Node = null

var current_speed: float = 30.0
var flight_distance: float = 0.0

var current_heading: float = 0.0  # Radians around global UP
var current_pitch: float = 0.0    # Radians nose up/down
var current_roll: float = 0.0     # Radians body banking

var last_pitch_input: float = 0.0
var last_yaw_input: float = 0.0
var last_roll_input: float = 0.0

# Standalone simulation fallback (for unit tests without CharacterBody3D)
var fallback_position: Vector3 = Vector3(0, 15, 0)
var fallback_basis: Basis = Basis()

func _ready() -> void:
	if has_node(body_path):
		body = get_node(body_path) as CharacterBody3D
	elif get_parent() is CharacterBody3D:
		body = get_parent() as CharacterBody3D
		
	if has_node(input_manager_path):
		input_manager = get_node(input_manager_path)
		
	if has_node(camera_rig_path):
		camera_rig = get_node(camera_rig_path)
		
	if has_node(visual_rig_path):
		visual_rig = get_node(visual_rig_path)
		
	reset_flight_state(Vector3(0, 15, 0) if body == null else body.global_position)

func _physics_process(delta: float) -> void:
	if not flight_enabled:
		return
		
	if delta <= 0.0:
		return
		
	# 1. Fetch normalized steering inputs [-1.0, 1.0]
	var pitch_in: float = 0.0
	var yaw_in: float = 0.0
	var roll_in: float = 0.0
	
	if input_manager != null and input_manager.has_method("get_pitch_input"):
		pitch_in = input_manager.get_pitch_input()
		yaw_in = input_manager.get_yaw_input()
		roll_in = input_manager.get_roll_input()
	else:
		pitch_in = Input.get_axis("steer_pitch_down", "steer_pitch_up")
		yaw_in = Input.get_axis("steer_yaw_left", "steer_yaw_right")
		roll_in = Input.get_axis("steer_roll_left", "steer_roll_right")
		
	last_pitch_input = pitch_in
	last_yaw_input = yaw_in
	last_roll_input = roll_in
		
	# 2. Aerodynamic speed integration
	_update_speed(pitch_in, delta)
	
	# 3. Attitude & banking kinematics
	_update_attitude(pitch_in, yaw_in, roll_in, delta)
	
	# 4. Integrate displacement & physics movement
	_apply_movement(delta)
	
	# 5. Emit telemetry signals
	_emit_telemetry()

func _update_speed(pitch_in: float, delta: float) -> void:
	# Negative pitch = dive (accelerate), Positive pitch = climb (decelerate)
	if pitch_in < -0.01:
		var dive_strength = -pitch_in
		current_speed += dive_strength * ACCELERATION_DIVE * delta
		current_speed = minf(current_speed, MAX_DIVE_SPEED)
	elif pitch_in > 0.01:
		var climb_strength = pitch_in
		current_speed -= climb_strength * DECELERATION_CLIMB * delta
		current_speed = maxf(current_speed, min_speed)
	else:
		# Level flight drag recovery toward cruise speed
		current_speed = move_toward(current_speed, CRUISE_SPEED, DRAG_DECELERATION * delta)
			
	current_speed = clampf(current_speed, min_speed, MAX_DIVE_SPEED)

func _update_attitude(pitch_in: float, yaw_in: float, roll_in: float, delta: float) -> void:
	# Yaw heading rate integration
	var yaw_rate_rad = deg_to_rad(MAX_YAW_RATE_DPS)
	current_heading -= yaw_in * yaw_rate_rad * delta
	current_heading = wrapf(current_heading, -PI, PI)
	
	# Target pitch
	var target_pitch_rad = pitch_in * deg_to_rad(MAX_PITCH_DEG)
	current_pitch = lerp_angle(current_pitch, target_pitch_rad, clampf(pitch_response_speed * delta, 0.0, 1.0))
	current_pitch = clampf(current_pitch, deg_to_rad(-MAX_PITCH_DEG), deg_to_rad(MAX_PITCH_DEG))
	
	# Coordinated banking: yaw induces roll, blended with manual roll override
	var target_roll_rad: float = 0.0
	if absf(yaw_in) > 0.001 and absf(roll_in) > 0.001:
		target_roll_rad = clampf(yaw_in * deg_to_rad(MAX_BANK_ANGLE_DEG) + roll_in * deg_to_rad(15.0), deg_to_rad(-MAX_BANK_ANGLE_DEG), deg_to_rad(MAX_BANK_ANGLE_DEG))
	elif absf(yaw_in) > 0.001:
		target_roll_rad = yaw_in * deg_to_rad(MAX_BANK_ANGLE_DEG)
	else:
		target_roll_rad = roll_in * deg_to_rad(MAX_BANK_ANGLE_DEG)

	current_roll = lerp_angle(current_roll, target_roll_rad, clampf(roll_response_speed * delta, 0.0, 1.0))
	current_roll = clampf(current_roll, deg_to_rad(-MAX_BANK_ANGLE_DEG), deg_to_rad(MAX_BANK_ANGLE_DEG))
	
	# Construct orthonormal orientation basis
	var b = Basis(Vector3.UP, current_heading)
	b = b.rotated(b.x, current_pitch)
	b = b.rotated(-b.z, current_roll)
	
	if body != null:
		body.global_transform.basis = b.orthonormalized()
	else:
		fallback_basis = b.orthonormalized()

func _apply_movement(delta: float) -> void:
	var fwd_vec: Vector3 = Vector3.FORWARD
	if body != null:
		fwd_vec = -body.global_transform.basis.z.normalized()
		body.velocity = fwd_vec * current_speed
		
		# 1. Aerodynamic ground cushion lift near terrain surface (within 3.5m)
		if body.get_world_3d() != null:
			var space_state = body.get_world_3d().direct_space_state
			if space_state != null:
				var query = PhysicsRayQueryParameters3D.create(
					body.global_position,
					body.global_position + Vector3.DOWN * 4.0,
					1 # Layer 1 (Environment)
				)
				query.exclude = [body.get_rid()]
				var hit = space_state.intersect_ray(query)
				if not hit.is_empty():
					var clearance = body.global_position.y - hit.position.y
					if clearance < 3.5 and clearance > 0.0:
						var lift_intensity = clampf((3.5 - clearance) / 3.5, 0.0, 1.0)
						body.velocity.y += lift_intensity * 14.0
						if current_pitch < deg_to_rad(8.0):
							current_pitch = lerp_angle(current_pitch, deg_to_rad(8.0), clampf(5.0 * delta * lift_intensity, 0.0, 1.0))
							
		body.move_and_slide()
		
		# 2. Slide collision reporting & peaceful tangential deflection
		var col_count = body.get_slide_collision_count()
		if col_count > 0:
			var avg_normal = Vector3.ZERO
			for i in range(col_count):
				var col = body.get_slide_collision(i)
				avg_normal += col.get_normal()
				collision_impact.emit(col.get_collider(), col.get_position(), col.get_normal())
				
			if avg_normal.length_squared() > 0.001:
				avg_normal = avg_normal.normalized()
				
				if avg_normal.y > 0.15:
					# Sloped ground/hill contact: Tangential slope glide
					var slide_dir = fwd_vec.slide(avg_normal).normalized()
					if slide_dir.length_squared() < 0.1:
						slide_dir = (Vector3.UP * 0.7 + avg_normal * 0.3).normalized()
					body.velocity = slide_dir * current_speed
					current_pitch = lerp_angle(current_pitch, deg_to_rad(12.0), clampf(6.0 * delta, 0.0, 1.0))
				else:
					# Near-vertical cliff, spire, or wall contact:
					if -fwd_vec.dot(avg_normal) < 0.65:
						# Glancing cliff deflection along surface
						var slide_dir = fwd_vec.slide(avg_normal).normalized()
						body.velocity = slide_dir * current_speed
						var target_h = atan2(-slide_dir.x, -slide_dir.z)
						current_heading = lerp_angle(current_heading, target_h, clampf(4.0 * delta, 0.0, 1.0))
					else:
						# Head-on cliff contact: Upward Ridge Lift (swoop up cliff face)
						var swoop_dir = (Vector3.UP * 0.8 + avg_normal * 0.2).normalized()
						body.velocity = swoop_dir * current_speed
						current_pitch = lerp_angle(current_pitch, deg_to_rad(22.0), clampf(6.0 * delta, 0.0, 1.0))
	else:
		fwd_vec = -fallback_basis.z.normalized()
		fallback_position += fwd_vec * current_speed * delta
		
	flight_distance += current_speed * delta

func _emit_telemetry() -> void:
	speed_changed.emit(current_speed, min_speed, MAX_DIVE_SPEED)
	distance_updated.emit(flight_distance)
	var alt = body.global_position.y if body != null else fallback_position.y
	altitude_changed.emit(alt)

# Public API methods
func reset_flight_state(start_position: Vector3 = Vector3(0, 15, 0)) -> void:
	current_speed = CRUISE_SPEED
	flight_distance = 0.0
	current_heading = 0.0
	current_pitch = 0.0
	current_roll = 0.0
	last_pitch_input = 0.0
	last_yaw_input = 0.0
	last_roll_input = 0.0
	fallback_position = start_position
	fallback_basis = Basis()
	
	if body != null:
		body.global_position = start_position
		body.global_transform.basis = Basis()
		body.velocity = Vector3(0, 0, -CRUISE_SPEED)
		
	if camera_rig != null and camera_rig.has_method("reset_camera"):
		camera_rig.reset_camera()
		
	speed_changed.emit(current_speed, min_speed, MAX_DIVE_SPEED)
	distance_updated.emit(flight_distance)
	altitude_changed.emit(start_position.y)

func set_flight_enabled(enabled: bool) -> void:
	flight_enabled = enabled
	if not enabled and body != null:
		body.velocity = Vector3.ZERO

func get_flight_distance() -> float:
	return flight_distance

func get_current_speed() -> float:
	return current_speed

func get_roll_degrees() -> float:
	return rad_to_deg(current_roll)

func get_pitch_degrees() -> float:
	return rad_to_deg(current_pitch)

func get_pitch_input() -> float:
	return last_pitch_input

func get_yaw_input() -> float:
	return last_yaw_input

func get_roll_input() -> float:
	return last_roll_input
