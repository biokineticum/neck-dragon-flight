extends Node

@export var cycle_seconds: float = 180.0
@export var player_path: NodePath = NodePath("../PlayerDragon")
@export var environment_path: NodePath = NodePath("../WorldEnvironment")
@export var sun_path: NodePath = NodePath("../DirectionalLight3D")

var elapsed: float = 0.0
var player: Node3D
var world_environment: WorldEnvironment
var sun: DirectionalLight3D
var rain: GPUParticles3D
var base_fog_density: float
var base_fog_color: Color
var base_sun_energy: float

func _ready() -> void:
	player = get_node_or_null(player_path) as Node3D
	world_environment = get_node_or_null(environment_path) as WorldEnvironment
	sun = get_node_or_null(sun_path) as DirectionalLight3D
	if world_environment == null or world_environment.environment == null or sun == null:
		push_error("WeatherDirector requires a WorldEnvironment and directional light.")
		set_process(false)
		return
	world_environment.environment = world_environment.environment.duplicate()
	base_fog_density = world_environment.environment.fog_density
	base_fog_color = world_environment.environment.fog_light_color
	base_sun_energy = sun.light_energy
	_build_rain()
	_apply_weather(0.0)

func _build_rain() -> void:
	rain = GPUParticles3D.new()
	rain.name = "Rain"
	rain.top_level = true
	rain.amount = 700
	rain.lifetime = 1.8
	rain.local_coords = false
	rain.visibility_aabb = AABB(Vector3(-60.0, -50.0, -60.0), Vector3(120.0, 100.0, 120.0))
	var particles = ParticleProcessMaterial.new()
	particles.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	particles.emission_box_extents = Vector3(28.0, 10.0, 28.0)
	particles.direction = Vector3(0.0, -1.0, 0.0)
	particles.spread = 5.0
	particles.gravity = Vector3(0.0, -16.0, 0.0)
	particles.initial_velocity_min = 12.0
	particles.initial_velocity_max = 18.0
	rain.process_material = particles
	var drop = QuadMesh.new()
	drop.size = Vector2(0.045, 0.8)
	var drop_material = StandardMaterial3D.new()
	drop_material.albedo_color = Color(0.67, 0.77, 0.82, 0.55)
	drop_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	drop_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	drop_material.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	drop.material = drop_material
	rain.draw_pass_1 = drop
	rain.emitting = false
	add_child(rain)

func _process(delta: float) -> void:
	if player != null:
		rain.global_position = player.global_position + Vector3.UP * 14.0
	elapsed = fposmod(elapsed + delta, maxf(cycle_seconds, 1.0))
	var cloudiness = 0.5 - 0.5 * cos(TAU * elapsed / maxf(cycle_seconds, 1.0))
	_apply_weather(cloudiness)

func _apply_weather(cloudiness: float) -> void:
	var amount = clampf(cloudiness, 0.0, 1.0)
	world_environment.environment.fog_density = base_fog_density * lerpf(1.0, 2.2, amount)
	world_environment.environment.fog_light_color = base_fog_color.lerp(Color(0.55, 0.62, 0.66), amount * 0.6)
	sun.light_energy = base_sun_energy * lerpf(1.0, 0.58, amount)
	rain.emitting = amount > 0.72
