shader_type spatial;
render_mode cull_disabled, diffuse_burley;

void fragment() {
	float streak = 0.5 + 0.5 * sin(UV.x * 80.0 + sin(UV.y * 18.0 - TIME * 3.5) * 2.5);
	float foam = 0.5 + 0.5 * sin(UV.x * 31.0 + UV.y * 22.0 - TIME * 5.0);
	ALBEDO = mix(vec3(0.35, 0.63, 0.69), vec3(0.85, 0.96, 0.98), streak * 0.45 + foam * 0.2);
	ROUGHNESS = 0.38;
}
