shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx;

varying vec3 world_position;

void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	VERTEX.y += 0.12 * sin(world_position.x * 0.12 + TIME * 1.2) * sin(world_position.z * 0.09 - TIME * 0.8);
}

void fragment() {
	float ripple = sin(world_position.x * 0.18 + TIME * 1.2) * sin(world_position.z * 0.16 - TIME * 0.9);
	ALBEDO = mix(vec3(0.035, 0.20, 0.25), vec3(0.10, 0.38, 0.42), ripple * 0.15 + 0.5);
	ROUGHNESS = 0.18;
	METALLIC = 0.08;
	SPECULAR = 0.8;
}
