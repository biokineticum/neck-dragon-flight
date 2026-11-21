shader_type spatial;
render_mode cull_disabled, diffuse_burley;

varying vec3 world_position;

void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	float bands = sin(world_position.y * 0.13 + sin(world_position.x * 0.06) * 1.4) * 0.5 + 0.5;
	float grain = sin(world_position.x * 0.24) * sin(world_position.z * 0.22) * 0.5 + 0.5;
	ALBEDO = mix(vec3(0.19, 0.20, 0.18), vec3(0.43, 0.40, 0.34), bands * 0.7 + grain * 0.3);
	ROUGHNESS = 0.95;
}
