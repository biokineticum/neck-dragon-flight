# ==============================================================================
# DragonVisualRig.gd - Procedural Visual Mesh Rig & Flight Kinematics
# ==============================================================================
# Milestone 3 / Requirement R4:
# Constructs dragon meshes (head, horns, eyes, neck, saddle, articulated wings)
# via ProceduralMeshGen.gd and executes dynamic flapping, heave/pitch bobbing,
# and anticipatory head yaw into turns.
# ==============================================================================
class_name DragonVisualRig
extends Node3D

const ProceduralMeshGen = preload("res://scripts/ProceduralMeshGen.gd")

@export var flight_controller_path: NodePath = NodePath("../FlightController")
@export var dragon_material: Material = preload("res://materials/dragon_scales.tres")

# Kinematic tuning parameters
@export var base_flap_frequency: float = 1.2       # Base flap Hz at cruise speed (30 m/s)
@export var base_cruise_speed: float = 30.0        # Nominal cruise speed in m/s
@export var wing_flap_amplitude_deg: float = 24.0  # Max wing flap rotation in degrees
@export var wing_feather_amplitude_deg: float = 5.0 # Max wing feather pitch rotation
@export var heave_amplitude: float = 0.1           # Torso heave displacement in meters
@export var pitch_bob_amplitude_deg: float = 2.2   # Torso pitch bob in degrees
@export var max_anticipatory_yaw_deg: float = 16.0 # Max anticipatory head yaw in degrees
@export var anticipatory_yaw_smoothing: float = 8.0 # Lerp factor for head turning

# Pivot nodes
var torso_pivot: Node3D = null
var neck_saddle_mesh: MeshInstance3D = null
var head_pivot: Node3D = null
var head_mesh: MeshInstance3D = null
var left_wing_pivot: Node3D = null
var left_wing_mesh: MeshInstance3D = null
var right_wing_pivot: Node3D = null
var right_wing_mesh: MeshInstance3D = null

# Kinematics runtime state
var flap_phase: float = 0.0
var current_flap_frequency: float = 1.2
var current_head_yaw: float = 0.0
var current_head_pitch: float = 0.0
var flight_controller: Node = null

func _ready() -> void:
	_build_or_bind_rig()
	if has_node(flight_controller_path):
		flight_controller = get_node(flight_controller_path)

func _build_or_bind_rig() -> void:
	# 1. Torso Pivot (Root of heave and pitch bobbing)
	torso_pivot = get_node_or_null("TorsoPivot") as Node3D
	if torso_pivot == null:
		torso_pivot = Node3D.new()
		torso_pivot.name = "TorsoPivot"
		add_child(torso_pivot)

	# 2. Neck and Saddle Mesh
	neck_saddle_mesh = torso_pivot.get_node_or_null("NeckSaddleMesh") as MeshInstance3D
	if neck_saddle_mesh == null:
		neck_saddle_mesh = MeshInstance3D.new()
		neck_saddle_mesh.name = "NeckSaddleMesh"
		neck_saddle_mesh.mesh = ProceduralMeshGen.generate_dragon_neck_saddle()
		if dragon_material != null:
			neck_saddle_mesh.material_override = dragon_material
		torso_pivot.add_child(neck_saddle_mesh)

	# 3. Head Pivot & Mesh (Neck terminates at Z = -1.40, Y = 0.10)
	head_pivot = torso_pivot.get_node_or_null("HeadPivot") as Node3D
	if head_pivot == null:
		head_pivot = Node3D.new()
		head_pivot.name = "HeadPivot"
		head_pivot.position = Vector3(0.0, 0.10, -1.40)
		torso_pivot.add_child(head_pivot)

	head_mesh = head_pivot.get_node_or_null("HeadMesh") as MeshInstance3D
	if head_mesh == null:
		head_mesh = MeshInstance3D.new()
		head_mesh.name = "HeadMesh"
		head_mesh.mesh = ProceduralMeshGen.generate_dragon_head()
		if dragon_material != null:
			head_mesh.material_override = dragon_material
		head_pivot.add_child(head_mesh)

	# 4. Left Wing Pivot & Mesh (Shoulder hinge at X = -0.40, Y = 0.05, Z = -0.20)
	left_wing_pivot = torso_pivot.get_node_or_null("LeftWingPivot") as Node3D
	if left_wing_pivot == null:
		left_wing_pivot = Node3D.new()
		left_wing_pivot.name = "LeftWingPivot"
		left_wing_pivot.position = Vector3(-0.40, 0.05, -0.20)
		torso_pivot.add_child(left_wing_pivot)

	left_wing_mesh = left_wing_pivot.get_node_or_null("LeftWingMesh") as MeshInstance3D
	if left_wing_mesh == null:
		left_wing_mesh = MeshInstance3D.new()
		left_wing_mesh.name = "LeftWingMesh"
		left_wing_mesh.position = Vector3(0.40, -0.05, 0.20) # Aligns shoulder at pivot origin
		left_wing_mesh.mesh = ProceduralMeshGen.generate_dragon_wing(true)
		if dragon_material != null:
			left_wing_mesh.material_override = dragon_material
		left_wing_pivot.add_child(left_wing_mesh)

	# 5. Right Wing Pivot & Mesh (Shoulder hinge at X = 0.40, Y = 0.05, Z = -0.20)
	right_wing_pivot = torso_pivot.get_node_or_null("RightWingPivot") as Node3D
	if right_wing_pivot == null:
		right_wing_pivot = Node3D.new()
		right_wing_pivot.name = "RightWingPivot"
		right_wing_pivot.position = Vector3(0.40, 0.05, -0.20)
		torso_pivot.add_child(right_wing_pivot)

	right_wing_mesh = right_wing_pivot.get_node_or_null("RightWingMesh") as MeshInstance3D
	if right_wing_mesh == null:
		right_wing_mesh = MeshInstance3D.new()
		right_wing_mesh.name = "RightWingMesh"
		right_wing_mesh.position = Vector3(-0.40, -0.05, 0.20) # Aligns shoulder at pivot origin
		right_wing_mesh.mesh = ProceduralMeshGen.generate_dragon_wing(false)
		if dragon_material != null:
			right_wing_mesh.material_override = dragon_material
		right_wing_pivot.add_child(right_wing_mesh)

func _process(delta: float) -> void:
	# 1. Fetch flight telemetry
	var current_speed: float = base_cruise_speed
	var yaw_input: float = 0.0
	var pitch_input: float = 0.0
	
	if is_instance_valid(flight_controller):
		if "current_speed" in flight_controller:
			current_speed = flight_controller.current_speed
		elif flight_controller.has_method("get_current_speed"):
			current_speed = flight_controller.get_current_speed()
			
		if flight_controller.has_method("get_yaw_input"):
			yaw_input = flight_controller.get_yaw_input()
		if flight_controller.has_method("get_pitch_input"):
			pitch_input = flight_controller.get_pitch_input()

	# 2. Compute dynamic flap frequency scaled by speed ratio
	var speed_ratio: float = clampf(current_speed / base_cruise_speed, 0.4, 2.2)
	current_flap_frequency = base_flap_frequency * speed_ratio
	flap_phase += TAU * current_flap_frequency * delta
	flap_phase = fposmod(flap_phase, TAU)

	# 3. Articulated Wing Flapping Kinematics
	var flap_sin: float = sin(flap_phase)
	var flap_cos: float = cos(flap_phase)
	var flap_rad: float = deg_to_rad(wing_flap_amplitude_deg)
	var feather_rad: float = deg_to_rad(wing_feather_amplitude_deg)

	# Left wing (+Z rotates down for -X extension)
	if left_wing_pivot != null:
		left_wing_pivot.rotation = Vector3(
			flap_cos * feather_rad,
			0.0,
			flap_sin * flap_rad
		)

	# Right wing (-Z rotates down for +X extension) - mirrored
	if right_wing_pivot != null:
		right_wing_pivot.rotation = Vector3(
			flap_cos * feather_rad,
			0.0,
			-flap_sin * flap_rad
		)

	# 4. Torso Heave (0.1m) and Pitch Bobbing (2.2 deg)
	if torso_pivot != null:
		torso_pivot.position.y = flap_sin * heave_amplitude
		torso_pivot.rotation.x = sin(flap_phase + 0.25) * deg_to_rad(pitch_bob_amplitude_deg)

	# 5. Anticipatory Head Yaw into Turns
	if head_pivot != null:
		var target_head_yaw: float = -yaw_input * deg_to_rad(max_anticipatory_yaw_deg)
		var head_blend = 1.0 - exp(-maxf(anticipatory_yaw_smoothing, 0.0) * delta)
		current_head_yaw = lerp(current_head_yaw, target_head_yaw, head_blend)
		
		var target_head_pitch: float = pitch_input * deg_to_rad(6.0)
		current_head_pitch = lerp(current_head_pitch, target_head_pitch, head_blend)
		
		head_pivot.rotation = Vector3(current_head_pitch, current_head_yaw, 0.0)

# Public inspection helpers for automated headless tests
func get_flap_phase() -> float:
	return flap_phase

func get_current_flap_frequency() -> float:
	return current_flap_frequency

func get_head_yaw() -> float:
	return current_head_yaw

func get_torso_heave() -> float:
	return torso_pivot.position.y if torso_pivot != null else 0.0

func get_torso_pitch() -> float:
	return torso_pivot.rotation.x if torso_pivot != null else 0.0

func get_left_wing_rotation() -> Vector3:
	return left_wing_pivot.rotation if left_wing_pivot != null else Vector3.ZERO

func get_right_wing_rotation() -> Vector3:
	return right_wing_pivot.rotation if right_wing_pivot != null else Vector3.ZERO
