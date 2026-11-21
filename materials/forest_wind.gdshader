shader_type spatial;
render_mode diffuse_burley;

void vertex() {
	float canopy = smoothstep(2.0, 8.0, VERTEX.y);
	VERTEX.x += sin(TIME * 1.1 + float(INSTANCE_ID) * 0.73) * 0.28 * canopy;
	VERTEX.z += cos(TIME * 0.8 + float(INSTANCE_ID) * 0.51) * 0.16 * canopy;
}

void fragment() {
	ALBEDO = COLOR.rgb;
	ROUGHNESS = 0.95;
}
