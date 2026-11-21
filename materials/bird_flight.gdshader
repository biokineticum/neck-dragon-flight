shader_type spatial;
render_mode cull_disabled, diffuse_burley;

void vertex() {
	float wing = abs(VERTEX.x) / 2.2;
	VERTEX.y += wing * sin(TIME * 5.0 + float(INSTANCE_ID) * 1.7) * 0.7;
}

void fragment() {
	ALBEDO = vec3(0.12, 0.15, 0.17);
	ROUGHNESS = 1.0;
}
