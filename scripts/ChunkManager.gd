# ==============================================================================
# ChunkManager.gd - Peaceful Open World Exploration Landscape Manager
# ==============================================================================
# Milestone M1 / Requirements R1, R4:
# - Replaces 1D obstacle canyon chunk conveyor belt with a 3000m x 3000m static realm.
# - Lush central valley basin (Y=10-35m), rolling hills, mountain passes (Y=120-280m),
#   and outer boundary ridges (Y=320-380m) shaded with rock_snow_triplanar shader.
# - Forest MultiMesh: 2000+ stylized fairytale trees with passthrough collision.
# - Sky & 3D Clouds: Procedural puffy cloud clusters (Y=90-250m) with passthrough navigation.
# - Soft boundary guidance: At R > 1350m, gentle breeze steers player back to valley center.
# - Backward-compatible API: Maintains setup_corridor(), reset_corridor(), update_player_position().
# ==============================================================================
class_name ChunkManager
extends Node3D

const ProceduralMeshGen = preload("res://scripts/ProceduralMeshGen.gd")
const WorldDetails = preload("res://scripts/WorldDetails.gd")

@export var chunk_scene: PackedScene = preload("res://scenes/ObstacleChunk.tscn")
@export var rock_material: Material = preload("res://materials/rock_snow_triplanar.tres")
@export var chunk_length: float = 200.0
@export var pool_size: int = 4
@export var master_seed: int = 42

# Open World Landscape Configuration
@export var world_size: float = 3000.0
@export var world_resolution: int = 140
@export var tree_count: int = 2200
@export var cloud_count: int = 42
@export var soft_boundary_radius: float = 1350.0

var chunk_pool: Array[Node3D] = []
var current_front_z: float = 0.0
var next_chunk_index: int = 0
var player_ref: Node3D = null

# Open World Scene Nodes
var landscape_mesh_instance: MeshInstance3D = null
var forest_multimesh_instance: MultiMeshInstance3D = null
var clouds_container: Node3D = null
var world_details: Node3D = null
var cloud_time: float = 0.0

func _ready() -> void:
	_build_open_world()
	if chunk_pool.is_empty():
		reset_corridor()

func setup_corridor(player: Node3D, p_seed: int = 42) -> void:
	player_ref = player
	master_seed = p_seed
	_build_open_world()
	reset_corridor()

func reset_chunks() -> void:
	reset_corridor()

func get_active_chunk_count() -> int:
	return chunk_pool.size()

## Build the 3000m x 3000m static exploration landscape, forests, and fly-through clouds
func _build_open_world() -> void:
	# 1. Clean existing open world nodes if rebuilding
	if is_instance_valid(landscape_mesh_instance):
		remove_child(landscape_mesh_instance)
		landscape_mesh_instance.queue_free()
	if is_instance_valid(forest_multimesh_instance):
		remove_child(forest_multimesh_instance)
		forest_multimesh_instance.queue_free()
	if is_instance_valid(clouds_container):
		remove_child(clouds_container)
		clouds_container.queue_free()
	if is_instance_valid(world_details):
		remove_child(world_details)
		world_details.queue_free()
		
	# 2. Generate 3000m x 3000m Static Exploration Landscape
	landscape_mesh_instance = MeshInstance3D.new()
	landscape_mesh_instance.name = "OpenWorldLandscape"
	var landscape_mesh = ProceduralMeshGen.generate_open_world_landscape(world_size, world_resolution, master_seed)
	landscape_mesh_instance.mesh = landscape_mesh
	if rock_material != null:
		landscape_mesh_instance.material_override = rock_material
	add_child(landscape_mesh_instance)
	
	# Attach StaticBody3D trimesh collider on Layer 1 (Environment)
	var landscape_body = StaticBody3D.new()
	landscape_body.name = "LandscapeCollider"
	landscape_body.collision_layer = 1
	landscape_body.collision_mask = 0
	var col = CollisionShape3D.new()
	col.name = "TrimeshShape"
	col.shape = landscape_mesh.create_trimesh_shape()
	if col.shape is ConcavePolygonShape3D:
		col.shape.backface_collision = true
	landscape_body.add_child(col)
	landscape_mesh_instance.add_child(landscape_body)
	
	# 3. Forests: 2000+ Fairytale Trees via MultiMeshInstance3D (Passthrough collision)
	_build_forests()
	
	# 4. Sky & Fly-Through 3D Puffy Clouds (Zero collision)
	_build_clouds()

	world_details = WorldDetails.new()
	world_details.name = "WorldDetails"
	add_child(world_details)
	world_details.build(world_size, world_resolution, master_seed)

## Procedural Forest Generation using GPU instancing
func _build_forests() -> void:
	forest_multimesh_instance = MultiMeshInstance3D.new()
	forest_multimesh_instance.name = "ForestMultiMesh"
	
	var mm = MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.instance_count = tree_count
	mm.mesh = ProceduralMeshGen.generate_fairytale_tree_mesh()
	var tree_material = ShaderMaterial.new()
	tree_material.shader = preload("res://materials/forest_wind.gdshader")
	forest_multimesh_instance.material_override = tree_material
	
	var rng = RandomNumberGenerator.new()
	rng.seed = master_seed + 104729
	
	var placed = 0
	var max_attempts = tree_count * 20
	var attempts = 0
	
	while placed < tree_count and attempts < max_attempts:
		attempts += 1
		var angle = rng.randf_range(0.0, TAU)
		var dist = rng.randf_range(40.0, 1150.0)
		var x = cos(angle) * dist
		var z = sin(angle) * dist
		var y = ProceduralMeshGen.sample_landscape_surface(x, z, world_size, world_resolution, master_seed)
		
		# Trees thrive in valley floor and gentle hill slopes (Y between 10m and 120m)
		if y < 10.0 or y > 125.0 or Vector2(x, z).distance_to(ProceduralMeshGen.LAKE_CENTER) < ProceduralMeshGen.LAKE_RADIUS + 35.0:
			continue
		if x > ProceduralMeshGen.RIVER_START and x < ProceduralMeshGen.RIVER_END and absf(z - ProceduralMeshGen.river_center_z(x)) < ProceduralMeshGen.RIVER_HALF_WIDTH + 20.0:
			continue
		var grove = sin(x * 0.009 + master_seed) * cos(z * 0.011 - master_seed)
		if rng.randf() > 0.55 + grove * 0.3:
			continue
			
		var scale_factor = rng.randf_range(0.85, 1.35)
		var t = Transform3D()
		t = t.scaled(Vector3(scale_factor, scale_factor, scale_factor))
		t = t.rotated(Vector3.UP, rng.randf_range(0.0, TAU))
		t.origin = Vector3(x, y - 0.25, z)
		
		mm.set_instance_transform(placed, t)
		
		# Lush natural fairytale foliage colors
		var altitude_tint = clampf((y - 30.0) / 95.0, 0.0, 1.0)
		var green = rng.randf_range(0.48, 0.75) - altitude_tint * 0.12
		var red = rng.randf_range(0.18, 0.32)
		var blue = rng.randf_range(0.12, 0.25) + altitude_tint * 0.08
		mm.set_instance_color(placed, Color(red, green, blue, 1.0))
		placed += 1
		
	mm.visible_instance_count = placed
	forest_multimesh_instance.multimesh = mm
	# Passthrough collision (no CollisionShape or physics body)
	add_child(forest_multimesh_instance)

## Procedural 3D Fly-Through Cloud Clusters in Sky
func _build_clouds() -> void:
	clouds_container = Node3D.new()
	clouds_container.name = "SkyCloudsContainer"
	add_child(clouds_container)
	
	var cloud_mat = StandardMaterial3D.new()
	cloud_mat.albedo_color = Color(0.78, 0.84, 0.90, 1.0)
	cloud_mat.roughness = 0.90
	
	var cloud_mesh = ProceduralMeshGen.generate_puffy_cloud_mesh()
	var rng = RandomNumberGenerator.new()
	rng.seed = master_seed + 77713
	
	for i in range(cloud_count):
		var angle = rng.randf_range(0.0, TAU)
		var dist = rng.randf_range(80.0, 1350.0)
		var cx = cos(angle) * dist
		var cz = sin(angle) * dist
		var cy = rng.randf_range(95.0, 240.0) # Flight altitudes
		
		var cloud_node = MeshInstance3D.new()
		cloud_node.name = "Cloud_%d" % i
		cloud_node.mesh = cloud_mesh
		cloud_node.material_override = cloud_mat
		cloud_node.position = Vector3(cx, cy, cz)
		cloud_node.set_meta("home", cloud_node.position)
		
		var scale_xz = rng.randf_range(0.85, 1.6)
		var scale_y = rng.randf_range(0.65, 1.2)
		cloud_node.scale = Vector3(scale_xz, scale_y, scale_xz)
		cloud_node.rotation.y = rng.randf_range(0.0, TAU)
		
		# Zero collision attached: Enables seamless fly-through exploration (R1)
		clouds_container.add_child(cloud_node)

func _process(delta: float) -> void:
	cloud_time = fposmod(cloud_time + delta, 3600.0)
	if is_instance_valid(clouds_container):
		for cloud in clouds_container.get_children():
			var home: Vector3 = cloud.get_meta("home")
			cloud.position = home + Vector3(sin(cloud_time * 0.025 + home.z * 0.002) * 12.0, 0.0, cos(cloud_time * 0.02 + home.x * 0.002) * 8.0)

## Reset corridor & maintain legacy chunk pool for test suite compatibility
func reset_corridor() -> void:
	for c in chunk_pool:
		if is_instance_valid(c):
			c.free()
	chunk_pool.clear()
	
	current_front_z = 0.0
	next_chunk_index = 0
	
	for i in range(pool_size):
		var chunk: Node3D = chunk_scene.instantiate()
		chunk.name = "Chunk_%d" % i
		add_child(chunk)
		var z_pos = -float(i) * chunk_length
		chunk.position = Vector3(0, 0, z_pos)
		
		# Clean canyon walls and spires from chunk scene so open world remains wide open
		var canyon = chunk.get_node_or_null("CanyonWalls")
		if canyon != null:
			canyon.mesh = null
			for ch in canyon.get_children():
				ch.queue_free()
		var obstacles = chunk.get_node_or_null("Obstacles")
		if obstacles != null:
			for ch in obstacles.get_children():
				ch.queue_free()
				
		next_chunk_index += 1
		chunk_pool.append(chunk)
		current_front_z = z_pos

func recycle_rear_chunk() -> void:
	if chunk_pool.is_empty():
		return
		
	var rear_chunk = chunk_pool[0]
	current_front_z -= chunk_length
	rear_chunk.position = Vector3(0, 0, current_front_z)
	next_chunk_index += 1
	chunk_pool.append(chunk_pool.pop_front())

## Soft boundary guidance at R > 1350m and player tracking
func update_player_position(pos: Vector3) -> void:
	# 1. Soft boundary steering at radius R > 1350m (smoothly turn back toward valley center)
	var r_xz = Vector2(pos.x, pos.z).length()
	if r_xz > soft_boundary_radius and player_ref != null:
		var dir_to_center = -Vector2(pos.x, pos.z).normalized()
		var target_heading = atan2(-dir_to_center.x, -dir_to_center.y)
		var fc = player_ref.find_child("FlightController", true, false)
		if fc != null and "current_heading" in fc:
			var over_dist = clampf((r_xz - soft_boundary_radius) / 150.0, 0.0, 1.0)
			# Gentle breeze smoothly rotates dragon heading toward center
			fc.current_heading = lerp_angle(fc.current_heading, target_heading, 0.035 * over_dist)
			
	# 2. Gentle sky ceiling guidance (if altitude Y > 320m, gently pitch down into troposphere)
	if pos.y > 320.0 and player_ref != null:
		var fc = player_ref.find_child("FlightController", true, false)
		if fc != null and "current_pitch" in fc:
			fc.current_pitch = lerp_angle(fc.current_pitch, deg_to_rad(-10.0), 0.04)

	# 3. Maintain legacy streaming recycling for test suites
	if not chunk_pool.is_empty():
		var player_z: float = pos.z
		if player_z > 0.0 and current_front_z <= 0.0:
			player_z = -player_z
		var rear_chunk = chunk_pool[0]
		var rear_chunk_end = rear_chunk.position.z - chunk_length
		if player_z < rear_chunk_end:
			recycle_rear_chunk()

func _physics_process(_delta: float) -> void:
	if player_ref != null:
		update_player_position(player_ref.global_position)
	elif not chunk_pool.is_empty():
		# Check if PlayerDragon exists in parent tree
		var player = get_parent().find_child("PlayerDragon", true, false)
		if player != null:
			player_ref = player
			update_player_position(player_ref.global_position)
