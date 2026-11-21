# ==============================================================================
# ProceduralMeshGen.gd - Standalone Procedural 3D Mesh Generator for Godot 4
# ==============================================================================
# Implements Requirement R4 (Zero external file dependencies):
# Generates all procedural 3D ArrayMeshes in pure GDScript using SurfaceTool
# and FastNoiseLite.
#
# Meshes provided:
# 1. generate_dragon_head() -> ArrayMesh
# 2. generate_dragon_neck_saddle() -> ArrayMesh
# 3. generate_dragon_wing(left: bool = true) -> ArrayMesh
# 4. generate_needle_spire(height, base_radius, seed_val) -> ArrayMesh
# 5. generate_rock_arch(span_width, clearance_height, seed_val) -> ArrayMesh
# 6. generate_canyon_walls(length, width, height, seed_val) -> ArrayMesh
# ==============================================================================
class_name ProceduralMeshGen
extends RefCounted

## 1. Dragon Head & Horns
static func generate_dragon_head() -> ArrayMesh:
	var st = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	# Coordinate frame: +X Right, +Y Up, -Z Forward.
	# Skull base at Z = 0.0, Snout extends forward to Z = -1.65.
	
	# Ring 0: Skull Base (Z = 0.0)
	var r0_crown = Vector3(0.00, 0.35, 0.00)
	var r0_brow_l = Vector3(-0.35, 0.22, 0.00)
	var r0_brow_r = Vector3(0.35, 0.22, 0.00)
	var r0_jaw_l = Vector3(-0.28, -0.15, 0.00)
	var r0_jaw_r = Vector3(0.28, -0.15, 0.00)
	var r0_chin = Vector3(0.00, -0.25, 0.00)
	
	# Ring 1: Mid Cranium & Brow (Z = -0.7)
	var r1_crown = Vector3(0.00, 0.38, -0.70)
	var r1_brow_l = Vector3(-0.32, 0.25, -0.70)
	var r1_brow_r = Vector3(0.32, 0.25, -0.70)
	var r1_jaw_l = Vector3(-0.24, -0.12, -0.70)
	var r1_jaw_r = Vector3(0.24, -0.12, -0.70)
	var r1_chin = Vector3(0.00, -0.20, -0.70)
	
	# Ring 2: Snout Midpoint (Z = -1.2)
	var r2_ridge = Vector3(0.00, 0.26, -1.20)
	var r2_snout_l = Vector3(-0.20, 0.15, -1.20)
	var r2_snout_r = Vector3(0.20, 0.15, -1.20)
	var r2_jaw_l = Vector3(-0.16, -0.08, -1.20)
	var r2_jaw_r = Vector3(0.16, -0.08, -1.20)
	var r2_chin = Vector3(0.00, -0.15, -1.20)
	
	# Snout Tip / Nostril Apex (Z = -1.65)
	var tip_top = Vector3(0.00, 0.18, -1.65)
	var tip_nost_l = Vector3(-0.12, 0.10, -1.65)
	var tip_nost_r = Vector3(0.12, 0.10, -1.65)
	var tip_chin = Vector3(0.00, -0.10, -1.65)
	
	var head_verts: Array[Vector3] = [
		r0_crown, r0_brow_l, r0_brow_r, r0_jaw_l, r0_jaw_r, r0_chin,
		r1_crown, r1_brow_l, r1_brow_r, r1_jaw_l, r1_jaw_r, r1_chin,
		r2_ridge, r2_snout_l, r2_snout_r, r2_jaw_l, r2_jaw_r, r2_chin,
		tip_top, tip_nost_l, tip_nost_r, tip_chin
	]
	
	for v in head_verts:
		st.set_uv(Vector2(v.x * 2.0 + 0.5, -v.z * 0.5))
		st.add_vertex(v)
		
	var add_quad = func(i0: int, i1: int, i2: int, i3: int) -> void:
		st.add_index(i0); st.add_index(i2); st.add_index(i1)
		st.add_index(i0); st.add_index(i3); st.add_index(i2)
		
	var add_tri = func(i0: int, i1: int, i2: int) -> void:
		st.add_index(i0); st.add_index(i1); st.add_index(i2)

	# Ring 0 -> Ring 1 quads
	add_quad.call(0, 6, 7, 1)
	add_quad.call(2, 8, 6, 0)
	add_quad.call(1, 7, 9, 3)
	add_quad.call(4, 10, 8, 2)
	add_quad.call(3, 9, 11, 5)
	add_quad.call(5, 11, 10, 4)
	
	# Ring 1 -> Ring 2 quads
	add_quad.call(6, 12, 13, 7)
	add_quad.call(8, 14, 12, 6)
	add_quad.call(7, 13, 15, 9)
	add_quad.call(10, 16, 14, 8)
	add_quad.call(9, 15, 17, 11)
	add_quad.call(11, 17, 16, 10)
	
	# Ring 2 -> Tip quads & triangles
	add_quad.call(12, 18, 19, 13)
	add_quad.call(14, 20, 18, 12)
	add_quad.call(13, 19, 21, 15)
	add_quad.call(16, 21, 20, 14)
	add_tri.call(15, 21, 17)
	add_tri.call(17, 21, 16)
	
	# Muzzle front cap
	add_tri.call(18, 20, 19)
	add_tri.call(19, 20, 21)
	
	# --- Swept-Back Curved Horns (Bezier Lofting) ---
	var vert_count_head = [head_verts.size()]
	var add_horn = func(root_p: Vector3, ctrl_p: Vector3, tip_p: Vector3, segments: int, sides: int) -> void:
		var prev_ring: Array[int] = []
		for s in range(segments + 1):
			var t: float = float(s) / float(segments)
			var center: Vector3 = (1.0 - t) * (1.0 - t) * root_p + 2.0 * (1.0 - t) * t * ctrl_p + t * t * tip_p
			var tangent: Vector3 = (2.0 * (1.0 - t) * (ctrl_p - root_p) + 2.0 * t * (tip_p - ctrl_p)).normalized()
			var up_ref = Vector3.UP
			if abs(tangent.dot(up_ref)) > 0.95:
				up_ref = Vector3.FORWARD
			var normal: Vector3 = tangent.cross(up_ref).normalized()
			var binormal: Vector3 = normal.cross(tangent).normalized()
			var radius: float = lerp(0.08, 0.005, t)
			
			var cur_ring: Array[int] = []
			for k in range(sides):
				var angle: float = (float(k) / float(sides)) * TAU
				var pt: Vector3 = center + (normal * cos(angle) + binormal * sin(angle)) * radius
				st.set_uv(Vector2(float(k) / float(sides), t))
				var idx: int = vert_count_head[0]
				vert_count_head[0] += 1
				st.add_vertex(pt)
				cur_ring.append(idx)
				
			if s > 0:
				for k in range(sides):
					var next_k = (k + 1) % sides
					var i0 = prev_ring[k]
					var i1 = cur_ring[k]
					var i2 = cur_ring[next_k]
					var i3 = prev_ring[next_k]
					st.add_index(i0); st.add_index(i2); st.add_index(i1)
					st.add_index(i0); st.add_index(i3); st.add_index(i2)
			prev_ring = cur_ring

	add_horn.call(Vector3(-0.22, 0.32, -0.10), Vector3(-0.35, 0.65, 0.25), Vector3(-0.48, 0.58, 0.85), 6, 6)
	add_horn.call(Vector3(0.22, 0.32, -0.10), Vector3(0.35, 0.65, 0.25), Vector3(0.48, 0.58, 0.85), 6, 6)
	
	# --- Diamond Faceted Glowing Eyes ---
	var add_eye = func(center: Vector3, is_left: bool) -> void:
		var dir: float = -1.0 if is_left else 1.0
		var apex = center + Vector3(dir * 0.08, 0.02, 0.05)
		var top = center + Vector3(0.00, 0.06, 0.00)
		var fwd = center + Vector3(0.00, 0.00, -0.10)
		var bot = center + Vector3(0.00, -0.06, 0.00)
		var rear = center + Vector3(0.00, 0.00, 0.10)
		
		var ai: int = vert_count_head[0]
		var ti: int = ai + 1
		var fi: int = ai + 2
		var bi: int = ai + 3
		var ri: int = ai + 4
		vert_count_head[0] += 5
		for pt in [apex, top, fwd, bot, rear]:
			st.set_uv(Vector2(0.5, 0.5))
			st.add_vertex(pt)
			
		if is_left:
			st.add_index(ai); st.add_index(ti); st.add_index(fi)
			st.add_index(ai); st.add_index(fi); st.add_index(bi)
			st.add_index(ai); st.add_index(bi); st.add_index(ri)
			st.add_index(ai); st.add_index(ri); st.add_index(ti)
		else:
			st.add_index(ai); st.add_index(fi); st.add_index(ti)
			st.add_index(ai); st.add_index(bi); st.add_index(fi)
			st.add_index(ai); st.add_index(ri); st.add_index(bi)
			st.add_index(ai); st.add_index(ti); st.add_index(ri)

	add_eye.call(Vector3(-0.30, 0.22, -0.55), true)
	add_eye.call(Vector3(0.30, 0.22, -0.55), false)

	st.generate_normals()
	return st.commit()



## 2. Dragon Neck & Saddle
static func generate_dragon_neck_saddle() -> ArrayMesh:
	var st = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	var neck_segments = 7
	var ring_sides = 8
	var p_base = Vector3(0, -0.25, 0.10)
	var p_mid = Vector3(0, -0.05, -0.65)
	var p_head = Vector3(0, 0.10, -1.40)
	
	for s in range(neck_segments + 1):
		var t: float = float(s) / float(neck_segments)
		var center: Vector3 = (1.0 - t) * (1.0 - t) * p_base + 2.0 * (1.0 - t) * t * p_mid + t * t * p_head
		var rx: float = lerp(0.42, 0.24, t)
		var ry: float = lerp(0.46, 0.26, t)
		
		for k in range(ring_sides):
			var angle: float = (float(k) / float(ring_sides)) * TAU
			var pt = center + Vector3(rx * cos(angle), ry * sin(angle), 0)
			if k == 2:
				pt.y += 0.08 # Dorsal crest spine
			st.set_uv(Vector2(float(k) / float(ring_sides), t * 2.0))
			st.add_vertex(pt)
			
		if s > 0:
			for k in range(ring_sides):
				var next_k = (k + 1) % ring_sides
				var i0 = (s - 1) * ring_sides + k
				var i1 = s * ring_sides + k
				var i2 = s * ring_sides + next_k
				var i3 = (s - 1) * ring_sides + next_k
				st.add_index(i0); st.add_index(i2); st.add_index(i1)
				st.add_index(i0); st.add_index(i3); st.add_index(i2)

	# Stylized Leather Saddle framing bottom cockpit view
	var saddle_start_idx = (neck_segments + 1) * ring_sides
	var saddle_z_steps = 4
	var saddle_u_steps = 6
	for sz in range(saddle_z_steps + 1):
		var tz: float = float(sz) / float(saddle_z_steps)
		var z_pos: float = lerp(0.15, 0.65, tz)
		var y_base: float = -0.32 + 0.12 * (tz - 0.4) * (tz - 0.4)
		for su in range(saddle_u_steps + 1):
			var tu: float = float(su) / float(saddle_u_steps)
			var u_angle: float = lerp(-PI * 0.75, -PI * 0.25, tu)
			var sx: float = 0.52 * cos(u_angle)
			var sy: float = y_base + 0.38 * sin(u_angle)
			st.set_uv(Vector2(tu, tz))
			st.add_vertex(Vector3(sx, sy, z_pos))
			
		if sz > 0:
			for su in range(saddle_u_steps):
				var i0 = saddle_start_idx + (sz - 1) * (saddle_u_steps + 1) + su
				var i1 = saddle_start_idx + sz * (saddle_u_steps + 1) + su
				var i2 = saddle_start_idx + sz * (saddle_u_steps + 1) + su + 1
				var i3 = saddle_start_idx + (sz - 1) * (saddle_u_steps + 1) + su + 1
				st.add_index(i0); st.add_index(i2); st.add_index(i1)
				st.add_index(i0); st.add_index(i3); st.add_index(i2)
				
	st.generate_normals()
	return st.commit()



## 3. Dragon Wings
static func generate_dragon_wing(left: bool = true) -> ArrayMesh:
	var st = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	var dir: float = -1.0 if left else 1.0
	
	var j_shoulder = Vector3(dir * 0.40, 0.05, -0.20)
	var j_elbow = Vector3(dir * 1.50, 0.35, -0.40)
	var j_wrist = Vector3(dir * 2.80, 0.60, -0.20)
	
	var f1_tip = Vector3(dir * 4.60, 0.35, -0.50)
	var f2_tip = Vector3(dir * 4.10, 0.05, 0.60)
	var f3_tip = Vector3(dir * 3.10, -0.15, 1.50)
	var flank_root = Vector3(dir * 0.35, -0.20, 1.10)
	
	var vert_idx = [0]
	var add_v = func(pt: Vector3, uv: Vector2) -> int:
		var idx: int = vert_idx[0]
		vert_idx[0] += 1
		st.set_uv(uv)
		st.add_vertex(pt)
		return idx
		
	var add_tri_sided = func(i0: int, i1: int, i2: int) -> void:
		if left:
			st.add_index(i0); st.add_index(i2); st.add_index(i1)
			st.add_index(i0); st.add_index(i1); st.add_index(i2)
		else:
			st.add_index(i0); st.add_index(i1); st.add_index(i2)
			st.add_index(i0); st.add_index(i2); st.add_index(i1)

	var add_quad_sided = func(i0: int, i1: int, i2: int, i3: int) -> void:
		add_tri_sided.call(i0, i1, i2)
		add_tri_sided.call(i0, i2, i3)

	# Volumetric 3D Wing Spars
	var make_spar = func(p1: Vector3, p2: Vector3, r1: float, r2: float) -> void:
		var d_vec: Vector3 = (p2 - p1).normalized()
		var u_vec = Vector3.UP
		if abs(d_vec.dot(u_vec)) > 0.95:
			u_vec = Vector3.FORWARD
		var n_vec: Vector3 = d_vec.cross(u_vec).normalized()
		var b_vec: Vector3 = n_vec.cross(d_vec).normalized()
		
		var idxs1: Array[int] = []
		var idxs2: Array[int] = []
		for k in range(4):
			var ang: float = float(k) * (PI * 0.5)
			var o1 = (n_vec * cos(ang) + b_vec * sin(ang)) * r1
			var o2 = (n_vec * cos(ang) + b_vec * sin(ang)) * r2
			idxs1.append(add_v.call(p1 + o1, Vector2(float(k) / 4.0, 0.0)))
			idxs2.append(add_v.call(p2 + o2, Vector2(float(k) / 4.0, 1.0)))
			
		for k in range(4):
			var next_k = (k + 1) % 4
			var i0 = idxs1[k]
			var i1 = idxs2[k]
			var i2 = idxs2[next_k]
			var i3 = idxs1[next_k]
			if left:
				st.add_index(i0); st.add_index(i1); st.add_index(i2)
				st.add_index(i0); st.add_index(i2); st.add_index(i3)
			else:
				st.add_index(i0); st.add_index(i1); st.add_index(i2)
				st.add_index(i0); st.add_index(i2); st.add_index(i3)

	make_spar.call(j_shoulder, j_elbow, 0.08, 0.06)
	make_spar.call(j_elbow, j_wrist, 0.06, 0.05)
	make_spar.call(j_wrist, f1_tip, 0.05, 0.02)
	make_spar.call(j_wrist, f2_tip, 0.04, 0.015)
	make_spar.call(j_wrist, f3_tip, 0.04, 0.015)
	
	# Double-Sided Wing Membrane Panels
	var m_shoulder = add_v.call(j_shoulder, Vector2(0.0, 0.0))
	var m_elbow = add_v.call(j_elbow, Vector2(0.2, 0.1))
	var m_wrist = add_v.call(j_wrist, Vector2(0.5, 0.2))
	var m_f1 = add_v.call(f1_tip, Vector2(1.0, 0.0))
	var m_f2 = add_v.call(f2_tip, Vector2(0.9, 0.6))
	var m_f3 = add_v.call(f3_tip, Vector2(0.7, 1.0))
	var m_root = add_v.call(flank_root, Vector2(0.1, 0.9))
	
	add_quad_sided.call(m_shoulder, m_elbow, m_wrist, m_root)
	add_tri_sided.call(m_wrist, m_f1, m_f2)
	add_tri_sided.call(m_wrist, m_f2, m_f3)
	add_tri_sided.call(m_wrist, m_f3, m_root)
	
	st.generate_normals()
	return st.commit()



## 4. Mountain Needle Spires
static func generate_needle_spire(height: float = 60.0, base_radius: float = 7.0, seed_val: int = 0) -> ArrayMesh:
	var st = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	var noise = FastNoiseLite.new()
	noise.seed = seed_val
	noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	noise.frequency = 0.05
	
	var rings = 10
	var radial_segments = 8
	var y_bottom: float = -25.0
	var total_height: float = height - y_bottom
	
	for r in range(rings):
		var tr: float = float(r) / float(rings - 1)
		var y: float = y_bottom + tr * total_height
		var current_radius: float = base_radius * (0.08 + 0.92 * pow(max(0.0, 1.0 - tr), 1.25))
		
		for s in range(radial_segments):
			var angle: float = (float(s) / float(radial_segments)) * TAU
			var cos_a: float = cos(angle)
			var sin_a: float = sin(angle)
			
			var n: float = noise.get_noise_3d(cos_a * 2.0, y * 0.1, sin_a * 2.0)
			var r_perturbed: float = current_radius * (1.0 + 0.35 * n)
			var px: float = r_perturbed * cos_a
			var pz: float = r_perturbed * sin_a
			
			st.set_uv(Vector2(float(s) / float(radial_segments), tr * 4.0))
			st.add_vertex(Vector3(px, y, pz))
			
		if r > 0:
			for s in range(radial_segments):
				var next_s = (s + 1) % radial_segments
				var i0 = (r - 1) * radial_segments + s
				var i1 = r * radial_segments + s
				var i2 = r * radial_segments + next_s
				var i3 = (r - 1) * radial_segments + next_s
				st.add_index(i0); st.add_index(i2); st.add_index(i1)
				st.add_index(i0); st.add_index(i3); st.add_index(i2)
				
	var apex_idx = rings * radial_segments
	st.set_uv(Vector2(0.5, 1.0))
	st.add_vertex(Vector3(0, height + 2.0, 0))
	var top_ring_start = (rings - 1) * radial_segments
	for s in range(radial_segments):
		var next_s = (s + 1) % radial_segments
		st.add_index(top_ring_start + s)
		st.add_index(top_ring_start + next_s)
		st.add_index(apex_idx)
		
	st.generate_normals()
	return st.commit()



## 5. High-Mountain Rock Arches
static func generate_rock_arch(span_width: float = 42.0, clearance_height: float = 24.0, seed_val: int = 0) -> ArrayMesh:
	var st = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	var noise = FastNoiseLite.new()
	noise.seed = seed_val
	noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	noise.frequency = 0.08
	
	var arc_slices = 16
	var pillar_slices = 4
	var tube_sides = 8
	var arch_radius: float = 3.8
	var half_span: float = span_width * 0.5
	var y_floor: float = -25.0
	var eff_height: float = clearance_height + arch_radius
	
	var ring_centers: Array[Vector3] = []
	var ring_tangents: Array[Vector3] = []
	
	for p in range(pillar_slices):
		var tp: float = float(p) / float(pillar_slices)
		var y: float = lerp(y_floor, 0.0, tp)
		ring_centers.append(Vector3(-half_span, y, 0.0))
		ring_tangents.append(Vector3.UP)
		
	for i in range(arc_slices + 1):
		var theta: float = (float(i) / float(arc_slices)) * PI
		var cx: float = -half_span * cos(theta)
		var cy: float = eff_height * sin(theta)
		ring_centers.append(Vector3(cx, cy, 0.0))
		var tx: float = half_span * sin(theta)
		var ty: float = eff_height * cos(theta)
		ring_tangents.append(Vector3(tx, ty, 0.0).normalized())
		
	for p in range(1, pillar_slices + 1):
		var tp: float = float(p) / float(pillar_slices)
		var y: float = lerp(0.0, y_floor, tp)
		ring_centers.append(Vector3(half_span, y, 0.0))
		ring_tangents.append(Vector3.DOWN)
		
	var total_rings = ring_centers.size()
	for r in range(total_rings):
		var center: Vector3 = ring_centers[r]
		var tangent: Vector3 = ring_tangents[r]
		var normal: Vector3 = Vector3(-tangent.y, tangent.x, 0.0).normalized()
		var binormal = Vector3.BACK
		
		var dist_from_crown: float = abs(center.x) / half_span
		var local_radius: float = lerp(arch_radius * 0.85, arch_radius * 1.2, dist_from_crown)
		
		for k in range(tube_sides):
			var phi: float = (float(k) / float(tube_sides)) * TAU
			var n_val: float = noise.get_noise_3d(center.x * 0.2, center.y * 0.2 + phi, float(k))
			var r_disp: float = local_radius * (1.0 + 0.25 * n_val)
			var pt = center + (normal * cos(phi) + binormal * sin(phi)) * r_disp
			st.set_uv(Vector2(float(k) / float(tube_sides), float(r) / float(total_rings) * 5.0))
			st.add_vertex(pt)
			
		if r > 0:
			for k in range(tube_sides):
				var next_k = (k + 1) % tube_sides
				var i0 = (r - 1) * tube_sides + k
				var i1 = r * tube_sides + k
				var i2 = r * tube_sides + next_k
				var i3 = (r - 1) * tube_sides + next_k
				st.add_index(i0); st.add_index(i1); st.add_index(i2)
				st.add_index(i0); st.add_index(i2); st.add_index(i3)
				
	st.generate_normals()
	return st.commit()



## Valley Curvature Centerline Function
static func get_valley_center(z_world: float) -> float:
	return sin(z_world * 0.0055) * 36.0 + sin(z_world * 0.013 + 1.1) * 18.0

## 6. Canyon Walls
static func generate_canyon_walls(length: float = 200.0, width: float = 85.0, height: float = 130.0, seed_val: int = 0, start_z_world: float = 0.0) -> ArrayMesh:
	var st = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	var noise = FastNoiseLite.new()
	noise.seed = seed_val
	noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	noise.frequency = 0.035
	
	var z_segments = 20
	var half_w: float = width * 0.5
	var y_floor: float = -25.0
	var y_top: float = height + y_floor
	
	var tiers: Array[Dictionary] = [
		{"x_off": -4.0, "y": y_floor},
		{"x_off": 0.0, "y": y_floor + 18.0},
		{"x_off": -6.5, "y": y_floor + 55.0},
		{"x_off": 5.0, "y": y_top},
		{"x_off": 50.0, "y": y_top + 15.0}
	]
	var y_tier_count = tiers.size()
	var verts_per_side = (z_segments + 1) * y_tier_count
	
	var sides = [-1.0, 1.0]
	for s_idx in range(sides.size()):
		var side: float = sides[s_idx]
		var is_left: bool = (side < 0.0)
		var vert_offset = s_idx * verts_per_side
		
		for zi in range(z_segments + 1):
			var tz: float = float(zi) / float(z_segments)
			var z: float = -tz * length
			var current_z_world: float = start_z_world + z
			var x_center: float = get_valley_center(current_z_world)
			
			for ti in range(y_tier_count):
				var tier: Dictionary = tiers[ti]
				var ty: float = float(ti) / float(y_tier_count - 1)
				
				var tier_y: float = tier["y"]
				var tier_x_off: float = tier["x_off"]
				var n: float = noise.get_noise_2d(tier_y * 0.1, z * 0.04) * 6.5
				var x_base: float = half_w + tier_x_off
				var x: float = x_center + side * (x_base + n)
				var y: float = tier_y + noise.get_noise_2d(x * 0.05, z * 0.05) * 4.0
				
				st.set_uv(Vector2(tz * 8.0, ty * 4.0))
				st.add_vertex(Vector3(x, y, z))
				
			if zi > 0:
				for ti in range(y_tier_count - 1):
					var i0 = vert_offset + (zi - 1) * y_tier_count + ti
					var i1 = vert_offset + zi * y_tier_count + ti
					var i2 = vert_offset + zi * y_tier_count + ti + 1
					var i3 = vert_offset + (zi - 1) * y_tier_count + ti + 1
					
					if is_left:
						st.add_index(i0); st.add_index(i2); st.add_index(i1)
						st.add_index(i0); st.add_index(i3); st.add_index(i2)
					else:
						st.add_index(i0); st.add_index(i1); st.add_index(i2)
						st.add_index(i0); st.add_index(i2); st.add_index(i3)
						
	st.generate_normals()
	return st.commit()

## =============================================================================
## 7. Open World Landscape, Fairytale Forests & Fly-Through Puffy Clouds
## =============================================================================

## Procedural Open World Height Evaluation Function
const LAKE_CENTER: Vector2 = Vector2(380.0, -320.0)
const LAKE_RADIUS: float = 100.0
const LAKE_LEVEL: float = 12.0
const RIVER_START: float = 380.0
const RIVER_END: float = 1100.0
const RIVER_FALL: float = 760.0
const RIVER_HALF_WIDTH: float = 28.0
const SETTLEMENT_CENTERS: Array[Vector2] = [Vector2(-320.0, -270.0), Vector2(130.0, -600.0), Vector2(510.0, 220.0)]

static func river_center_z(x: float) -> float:
	var distance = x - RIVER_START
	return LAKE_CENTER.y - distance * 0.22 + 32.0 * sin(distance * 0.007)

static func river_half_width(x: float) -> float:
	return RIVER_HALF_WIDTH * (0.82 + 0.10 * sin(x * 0.016) + 0.08 * cos(x * 0.033))

static func river_level(x: float) -> float:
	return LAKE_LEVEL + maxf(x - RIVER_START, 0.0) * 0.018 + (30.0 if x > RIVER_FALL else 0.0)

static func get_landscape_height(x: float, z: float, seed_val: int = 42) -> float:
	var height = _natural_landscape_height(x, z, seed_val)
	for center in SETTLEMENT_CENTERS:
		var distance = Vector2(x, z).distance_to(center)
		if distance < 135.0:
			var clearing = 1.0 - smoothstep(85.0, 135.0, distance)
			return lerpf(height, _natural_landscape_height(center.x, center.y, seed_val), clearing)
	return height

static func _natural_landscape_height(x: float, z: float, seed_val: int) -> float:
	var r = sqrt(x * x + z * z)
	
	# Radial basin profile:
	# r < 300: flat valley floor (12.0m to 25.0m)
	# r in [300, 1000]: rolling hills and mountain ridges (25.0m to 200.0m)
	# r > 1000: outer mountain crests (200.0m to 360.0m)
	var radial_factor: float = 0.0
	if r < 250.0:
		radial_factor = 0.0
	elif r < 900.0:
		radial_factor = smoothstep(250.0, 900.0, r) * 0.55
	else:
		radial_factor = 0.55 + smoothstep(900.0, 1450.0, r) * 0.45
		
	var base_h = 14.0 + radial_factor * 280.0
	
	# Multi-octave undulating terrain harmonics
	var s_seed: float = float(seed_val % 1000) * 0.13
	var h1 = sin(x * 0.0042 + s_seed) * cos(z * 0.0038 + s_seed * 1.3) * 45.0
	var h2 = sin(x * 0.0095 - z * 0.0075 + s_seed * 0.7) * 22.0
	var h3 = cos(x * 0.018 + z * 0.015) * 8.0
	var h4 = sin(x * 0.035) * sin(z * 0.035) * 2.5
	
	# Center basin smoothing (keep spawn area and flight runway peaceful and flat)
	var basin_clearance = clampf((r - 180.0) / 220.0, 0.0, 1.0)
	var hills = (h1 + h2 + h3 + h4) * basin_clearance
	
	# Outer ridge enhancement
	var ridge_lift = 0.0
	if r > 1100.0:
		ridge_lift = pow((r - 1100.0) / 350.0, 1.8) * 90.0
		
	# Radial spurs and passes break up the circular outer ridge.
	var angle = atan2(z, x)
	var mountain_weight = smoothstep(450.0, 1050.0, r)
	var spurs = (sin(angle * 5.0 + s_seed) * 28.0 + sin(angle * 9.0 - s_seed) * 12.0) * mountain_weight
	var height = maxf(8.0, base_h + hills + ridge_lift + spurs)

	# A broad bowl keeps the lake below its shoreline and away from the spawn.
	var lake_distance = Vector2(x, z).distance_to(LAKE_CENTER)
	var lake_blend = 1.0 - smoothstep(LAKE_RADIUS - 12.0, LAKE_RADIUS + 80.0, lake_distance)
	height = lerpf(height, LAKE_LEVEL - 4.0, lake_blend)

	# The river bed rises upstream and drops at the falls before reaching the lake.
	var river_range = smoothstep(RIVER_START, RIVER_START + 40.0, x) * (1.0 - smoothstep(RIVER_END - 50.0, RIVER_END, x))
	var river_distance = absf(z - river_center_z(x))
	var river_blend = (1.0 - smoothstep(RIVER_HALF_WIDTH + 12.0, RIVER_HALF_WIDTH + 165.0, river_distance)) * river_range
	var bed = river_level(x) - 7.0
	var falls_cut = 1.0 - smoothstep(0.0, 55.0, absf(x - RIVER_FALL))
	bed = lerpf(bed, minf(bed, river_level(RIVER_FALL) - 7.0), falls_cut)
	return lerpf(height, minf(height, bed), river_blend)

## Match the triangle interpolation used by the visible and collision mesh.
static func sample_landscape_surface(x: float, z: float, size: float, resolution: int, seed_val: int) -> float:
	var step = size / float(resolution)
	var grid_x = clampf((x + size * 0.5) / step, 0.0, float(resolution))
	var grid_z = clampf((z + size * 0.5) / step, 0.0, float(resolution))
	var ix = mini(floori(grid_x), resolution - 1)
	var iz = mini(floori(grid_z), resolution - 1)
	var tx = grid_x - ix
	var tz = grid_z - iz
	var x0 = -size * 0.5 + ix * step
	var z0 = -size * 0.5 + iz * step
	var h00 = get_landscape_height(x0, z0, seed_val)
	var h11 = get_landscape_height(x0 + step, z0 + step, seed_val)
	if tx >= tz:
		var h10 = get_landscape_height(x0 + step, z0, seed_val)
		return h00 * (1.0 - tx) + h10 * (tx - tz) + h11 * tz
	var h01 = get_landscape_height(x0, z0 + step, seed_val)
	return h00 * (1.0 - tz) + h01 * (tz - tx) + h11 * tx

## 7.1 Large 3000m x 3000m Static Exploration Landscape
static func generate_open_world_landscape(size: float = 3000.0, resolution: int = 150, seed_val: int = 42) -> ArrayMesh:
	var st = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	st.set_smooth_group(0)
	
	var half_size = size * 0.5
	var step = size / float(resolution)
	var uv_scale = 35.0
	
	# Add vertices
	for zi in range(resolution + 1):
		var z = -half_size + float(zi) * step
		var tz = float(zi) / float(resolution)
		for xi in range(resolution + 1):
			var x = -half_size + float(xi) * step
			var tx = float(xi) / float(resolution)
			var y = get_landscape_height(x, z, seed_val)
			
			st.set_uv(Vector2(tx * uv_scale, tz * uv_scale))
			st.add_vertex(Vector3(x, y, z))
			
	# Generate triangles
	for zi in range(resolution):
		var row0 = zi * (resolution + 1)
		var row1 = (zi + 1) * (resolution + 1)
		for xi in range(resolution):
			var i0 = row0 + xi
			var i1 = row1 + xi
			var i2 = row1 + xi + 1
			var i3 = row0 + xi + 1
			
			st.add_index(i0)
			st.add_index(i2)
			st.add_index(i1)
			
			st.add_index(i0)
			st.add_index(i3)
			st.add_index(i2)
			
	st.generate_normals()
	return st.commit()

## 7.2 Stylized Fairytale Tree Mesh (Trunk + Tiered Canopy)
static func generate_fairytale_tree_mesh() -> ArrayMesh:
	var st = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	# Trunk: 6-sided cylinder
	var sides = 6
	var trunk_r = 0.55
	var trunk_h = 3.6
	
	for s in range(sides):
		var ang0 = float(s) / float(sides) * TAU
		var ang1 = float(s + 1) / float(sides) * TAU
		var v0_b = Vector3(cos(ang0) * trunk_r, 0.0, sin(ang0) * trunk_r)
		var v1_b = Vector3(cos(ang1) * trunk_r, 0.0, sin(ang1) * trunk_r)
		var v0_t = Vector3(cos(ang0) * trunk_r * 0.75, trunk_h, sin(ang0) * trunk_r * 0.75)
		var v1_t = Vector3(cos(ang1) * trunk_r * 0.75, trunk_h, sin(ang1) * trunk_r * 0.75)
		
		# Trunk quad
		st.set_uv(Vector2(float(s) / float(sides), 0.0))
		st.add_vertex(v0_b)
		st.set_uv(Vector2(float(s + 1) / float(sides), 0.0))
		st.add_vertex(v1_b)
		st.set_uv(Vector2(float(s + 1) / float(sides), 0.5))
		st.add_vertex(v1_t)
		
		st.set_uv(Vector2(float(s) / float(sides), 0.0))
		st.add_vertex(v0_b)
		st.set_uv(Vector2(float(s + 1) / float(sides), 0.5))
		st.add_vertex(v1_t)
		st.set_uv(Vector2(float(s) / float(sides), 0.5))
		st.add_vertex(v0_t)
		
	# Canopy: 3 stacked cones
	var tiers: Array[Dictionary] = [
		{"y_base": 2.2, "r_base": 3.0, "y_tip": 5.4},
		{"y_base": 4.0, "r_base": 2.4, "y_tip": 7.0},
		{"y_base": 5.6, "r_base": 1.7, "y_tip": 8.6}
	]
	var c_sides = 8
	for tier in tiers:
		var y_b: float = tier["y_base"]
		var r_b: float = tier["r_base"]
		var y_t: float = tier["y_tip"]
		var tip = Vector3(0.0, y_t, 0.0)
		
		for cs in range(c_sides):
			var a0 = float(cs) / float(c_sides) * TAU
			var a1 = float(cs + 1) / float(c_sides) * TAU
			var b0 = Vector3(cos(a0) * r_b, y_b, sin(a0) * r_b)
			var b1 = Vector3(cos(a1) * r_b, y_b, sin(a1) * r_b)
			
			# Cone side
			st.set_uv(Vector2(float(cs) / float(c_sides), 0.5))
			st.add_vertex(b0)
			st.set_uv(Vector2(float(cs + 1) / float(c_sides), 0.5))
			st.add_vertex(b1)
			st.set_uv(Vector2(0.5, 1.0))
			st.add_vertex(tip)
			
			# Cone bottom
			var center_b = Vector3(0.0, y_b, 0.0)
			st.set_uv(Vector2(0.5, 0.5))
			st.add_vertex(center_b)
			st.set_uv(Vector2(float(cs + 1) / float(c_sides), 0.5))
			st.add_vertex(b1)
			st.set_uv(Vector2(float(cs) / float(c_sides), 0.5))
			st.add_vertex(b0)
			
	st.generate_normals()
	return st.commit()

## 7.3 Procedural 3D Puffy Cloud Mesh
static func generate_puffy_cloud_mesh() -> ArrayMesh:
	var st = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	st.set_smooth_group(0)
	
	# Cloud puff spheres
	var puffs: Array[Dictionary] = [
		{"pos": Vector3(0, 0, 0), "r": 22.0},
		{"pos": Vector3(-18, -3, 5), "r": 16.0},
		{"pos": Vector3(17, 2, -4), "r": 17.0},
		{"pos": Vector3(4, -4, 16), "r": 14.0},
		{"pos": Vector3(-5, 3, -15), "r": 15.0},
		{"pos": Vector3(12, 1, 12), "r": 13.0},
		{"pos": Vector3(-12, 2, -10), "r": 14.0}
	]
	
	var lat_segs = 6
	var lon_segs = 8
	
	for puff in puffs:
		var cp: Vector3 = puff["pos"]
		var pr: float = puff["r"]
		
		for lat in range(lat_segs):
			var theta0 = float(lat) / float(lat_segs) * PI
			var theta1 = float(lat + 1) / float(lat_segs) * PI
			
			for lon in range(lon_segs):
				var phi0 = float(lon) / float(lon_segs) * TAU
				var phi1 = float(lon + 1) / float(lon_segs) * TAU
				
				var v00 = cp + Vector3(sin(theta0) * cos(phi0), cos(theta0), sin(theta0) * sin(phi0)) * pr
				var v01 = cp + Vector3(sin(theta0) * cos(phi1), cos(theta0), sin(theta0) * sin(phi1)) * pr
				var v10 = cp + Vector3(sin(theta1) * cos(phi0), cos(theta1), sin(theta1) * sin(phi0)) * pr
				var v11 = cp + Vector3(sin(theta1) * cos(phi1), cos(theta1), sin(theta1) * sin(phi1)) * pr
				
				st.set_uv(Vector2(float(lon) / float(lon_segs), float(lat) / float(lat_segs)))
				st.add_vertex(v00)
				st.set_uv(Vector2(float(lon + 1) / float(lon_segs), float(lat + 1) / float(lat_segs)))
				st.add_vertex(v11)
				st.set_uv(Vector2(float(lon + 1) / float(lon_segs), float(lat) / float(lat_segs)))
				st.add_vertex(v01)
				
				st.set_uv(Vector2(float(lon) / float(lon_segs), float(lat) / float(lat_segs)))
				st.add_vertex(v00)
				st.set_uv(Vector2(float(lon) / float(lon_segs), float(lat + 1) / float(lat_segs)))
				st.add_vertex(v10)
				st.set_uv(Vector2(float(lon + 1) / float(lon_segs), float(lat + 1) / float(lat_segs)))
				st.add_vertex(v11)
				
	st.index()
	st.generate_normals()
	return st.commit()
