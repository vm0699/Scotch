# Scotch Importer — SketchUp model builder (Stage 15.4)
#
# Reads a parsed Scotch project Hash (from Importer.load_json) and builds a
# full editable SketchUp model:
#
#   Ground slab     — S-SITE tag, Scotch_Ground material
#   Room walls      — S-ROOMS tag, washer pushpull → hollow walls
#   Door voids      — vertical face on inner wall surface + pushpull through
#   Window voids    — elevated vertical face + pushpull + glass material
#   3D text labels  — S-LABELS tag, room name + area at centroid
#   Roof slab       — S-ROOF tag, Scotch_Roof material
#
# Tags: S-SITE · S-ROOMS · S-ROOF · S-LABELS · S-OPENINGS
#
# All dimensions in project.json are in feet; SketchUp uses inches (× 12).

module ScotchImporter
  module Builder
    FT     = 12.0  # inches per foot
    WALL_T = 0.5   # ft — total wall thickness (0.25 ft each side)
    SLAB_T = 0.5   # ft — slab thickness
    SILL_H = 2.5   # ft — window sill
    WIN_H  = 4.0   # ft — window opening height

    ROOM_COLORS = {
      'living'         => [235, 225, 205],
      'dining'         => [235, 228, 210],
      'kitchen'        => [235, 230, 215],
      'master_bedroom' => [220, 205, 200],
      'bedroom'        => [230, 215, 210],
      'bathroom'       => [215, 230, 235],
      'balcony'        => [220, 225, 215],
      'parking'        => [200, 200, 200],
      'storage'        => [215, 215, 210],
      'study'          => [230, 225, 215],
      'foyer'          => [225, 220, 210],
      'corridor'       => [230, 228, 220],
      'seating'        => [235, 225, 205],
      'service'        => [215, 215, 215],
    }.freeze
    DEFAULT_COLOR = [240, 238, 235].freeze

    # Entry point: build the full model from a parsed Scotch project Hash.
    def self.build(data)
      model    = Sketchup.active_model
      entities = model.entities
      mats     = model.materials

      # Set model units to feet (LengthUnit 1 = feet in SketchUp)
      opts = model.options['UnitsOptions']
      opts['LengthUnit'] = 1 if opts

      model.start_operation('Scotch Import', true)

      tags      = setup_tags(model)
      base_mats = setup_base_materials(mats)
      room_mats = setup_room_materials(data['rooms'] || [], mats)

      site     = data['site']     || {}
      building = data['building'] || {}
      sw       = (site['width']          || 30).to_f
      sd       = (site['depth']          || 50).to_f
      fh       = (building['floor_height'] || 10).to_f

      build_ground_slab(entities, tags, base_mats, sw, sd)
      build_rooms(entities, tags, base_mats, room_mats,
                  data['rooms'] || [], data['doors'] || [], data['windows'] || [], fh)
      build_roof(entities, tags, base_mats, sw, sd, fh)
      add_room_labels(entities, tags, data['rooms'] || [])
      set_camera(model, sw, sd, fh)

      model.commit_operation
    end

    # ── Tag helpers ──────────────────────────────────────────────────────────

    def self.setup_tags(model)
      {
        site:   ensure_tag(model, 'S-SITE'),
        rooms:  ensure_tag(model, 'S-ROOMS'),
        roof:   ensure_tag(model, 'S-ROOF'),
        labels: ensure_tag(model, 'S-LABELS'),
        open:   ensure_tag(model, 'S-OPENINGS'),
      }
    end

    def self.ensure_tag(model, name)
      model.layers[name] || model.layers.add(name)
    end

    # ── Material helpers ─────────────────────────────────────────────────────

    def self.ensure_mat(mats, name, r, g, b, alpha = 255)
      m = mats[name] || mats.add(name)
      m.color = Sketchup::Color.new(r, g, b, alpha)
      m
    end

    def self.setup_base_materials(mats)
      {
        ground: ensure_mat(mats, 'Scotch_Ground', 210, 210, 200),
        wall:   ensure_mat(mats, 'Scotch_Wall',   245, 242, 238),
        roof:   ensure_mat(mats, 'Scotch_Roof',   175, 168, 158),
        glass:  ensure_mat(mats, 'Scotch_Glass',  180, 215, 245, 160),
      }
    end

    def self.setup_room_materials(rooms, mats)
      seen = {}
      rooms.each do |room|
        t = normalize_type(room['type'])
        next if seen.key?(t)
        color = ROOM_COLORS[t] || DEFAULT_COLOR
        name  = "Scotch_#{t.split('_').map(&:capitalize).join}"
        seen[t] = ensure_mat(mats, name, *color)
      end
      seen
    end

    def self.normalize_type(raw)
      (raw || 'generic').downcase.strip.gsub(/\s+/, '_')
    end

    # ── Geometry builders ────────────────────────────────────────────────────

    def self.build_ground_slab(entities, tags, base_mats, sw, sd)
      grp       = entities.add_group
      grp.layer = tags[:site]
      grp.name  = 'Ground Slab'
      ge        = grp.entities
      pts = [
        Geom::Point3d.new(0,       0,       -SLAB_T * FT),
        Geom::Point3d.new(sw * FT, 0,       -SLAB_T * FT),
        Geom::Point3d.new(sw * FT, sd * FT, -SLAB_T * FT),
        Geom::Point3d.new(0,       sd * FT, -SLAB_T * FT),
      ]
      face = ge.add_face(pts)
      face.material = base_mats[:ground]
      face.pushpull(SLAB_T * FT)
    end

    def self.build_rooms(entities, tags, base_mats, room_mats,
                         rooms, doors, windows, fh)
      rooms.each do |room|
        build_room(entities, tags, base_mats, room_mats,
                   room, doors, windows, fh)
      end
    end

    def self.build_room(entities, tags, base_mats, room_mats,
                        room, doors, windows, fh)
      rx   = room['x'].to_f
      ry   = room['y'].to_f
      rw   = room['width'].to_f
      rd   = room['depth'].to_f
      rid  = room['id']   || room['name']
      rname = room['name'] || rid
      rtype = normalize_type(room['type'])

      half = WALL_T / 2.0
      ox = rx - half
      oy = ry - half
      ow = rw + WALL_T
      od = rd + WALL_T

      rg       = entities.add_group
      rg.layer = tags[:rooms]
      rg.name  = "#{rname} [#{rid}]"
      re       = rg.entities

      # Outer wall boundary face at Z=0
      re.add_face([
        Geom::Point3d.new(ox * FT,        oy * FT,        0),
        Geom::Point3d.new((ox + ow) * FT, oy * FT,        0),
        Geom::Point3d.new((ox + ow) * FT, (oy + od) * FT, 0),
        Geom::Point3d.new(ox * FT,        (oy + od) * FT, 0),
      ])

      # Inner room floor face — creates washer shape with outer face
      room_mat = room_mats[rtype] || base_mats[:wall]
      inner = re.add_face([
        Geom::Point3d.new(rx * FT,        ry * FT,        0),
        Geom::Point3d.new((rx + rw) * FT, ry * FT,        0),
        Geom::Point3d.new((rx + rw) * FT, (ry + rd) * FT, 0),
        Geom::Point3d.new(rx * FT,        (ry + rd) * FT, 0),
      ])
      inner.material = room_mat if inner

      # Pushpull the washer to wall height → hollow walls
      washer = re.select do |e|
        e.is_a?(Sketchup::Face) && e.area > inner.area * 1.5
      rescue false
      end.first
      washer.pushpull(fh * FT) if washer

      # Door voids
      room_doors = doors.select { |d| d['room_id'] == rid }
      room_doors.each do |door|
        cut_opening(re, rx, ry, rw, rd,
                    door['wall'], door['offset'].to_f, door['width'].to_f,
                    0, fh, base_mats[:glass])
      end

      # Window voids
      room_wins = windows.select { |w| w['room_id'] == rid }
      room_wins.each do |win|
        cut_opening(re, rx, ry, rw, rd,
                    win['wall'], win['offset'].to_f, win['width'].to_f,
                    SILL_H, SILL_H + WIN_H, base_mats[:glass])
      end
    end

    # Cut a rectangular void in the wall by drawing a vertical face on the
    # inner wall surface and pushpulling it through the wall thickness.
    def self.cut_opening(re, rx, ry, rw, rd, wall, off, wid, z_bot, z_top, glass_mat)
      pts = opening_points(rx, ry, rw, rd, wall, off, wid, z_bot, z_top)
      return unless pts

      begin
        face = re.add_face(pts)
        face.pushpull(WALL_T * FT) if face  # cuts toward exterior
        face.material = glass_mat if face && !face.deleted?
      rescue
        # Geometry may fail on edge cases; skip gracefully
      end
    end

    # Return an Array of Geom::Point3d for a vertical opening face on *wall*.
    # Winding chosen so that pushpull(WALL_T*FT) goes toward the exterior.
    #   North → normal −Y,  South → normal +Y
    #   East  → normal +X,  West  → normal −X
    def self.opening_points(rx, ry, rw, rd, wall, off, wid, z_bot, z_top)
      case (wall || 'north').downcase
      when 'north'
        y = ry
        x0, x1 = rx + off, rx + off + wid
        [
          Geom::Point3d.new(x0 * FT, y * FT, z_bot * FT),
          Geom::Point3d.new(x1 * FT, y * FT, z_bot * FT),
          Geom::Point3d.new(x1 * FT, y * FT, z_top * FT),
          Geom::Point3d.new(x0 * FT, y * FT, z_top * FT),
        ]
      when 'south'
        y = ry + rd
        x0, x1 = rx + off, rx + off + wid
        [
          Geom::Point3d.new(x0 * FT, y * FT, z_bot * FT),
          Geom::Point3d.new(x0 * FT, y * FT, z_top * FT),
          Geom::Point3d.new(x1 * FT, y * FT, z_top * FT),
          Geom::Point3d.new(x1 * FT, y * FT, z_bot * FT),
        ]
      when 'east'
        x = rx + rw
        y0, y1 = ry + off, ry + off + wid
        [
          Geom::Point3d.new(x * FT, y0 * FT, z_bot * FT),
          Geom::Point3d.new(x * FT, y1 * FT, z_bot * FT),
          Geom::Point3d.new(x * FT, y1 * FT, z_top * FT),
          Geom::Point3d.new(x * FT, y0 * FT, z_top * FT),
        ]
      when 'west'
        x = rx
        y0, y1 = ry + off, ry + off + wid
        [
          Geom::Point3d.new(x * FT, y0 * FT, z_bot * FT),
          Geom::Point3d.new(x * FT, y0 * FT, z_top * FT),
          Geom::Point3d.new(x * FT, y1 * FT, z_top * FT),
          Geom::Point3d.new(x * FT, y1 * FT, z_bot * FT),
        ]
      end
    end

    def self.build_roof(entities, tags, base_mats, sw, sd, fh)
      grp       = entities.add_group
      grp.layer = tags[:roof]
      grp.name  = 'Roof Slab'
      ge        = grp.entities
      pts = [
        Geom::Point3d.new(0,       0,       fh * FT),
        Geom::Point3d.new(sw * FT, 0,       fh * FT),
        Geom::Point3d.new(sw * FT, sd * FT, fh * FT),
        Geom::Point3d.new(0,       sd * FT, fh * FT),
      ]
      face = ge.add_face(pts)
      face.material = base_mats[:roof]
      face.pushpull(SLAB_T * FT)
    end

    def self.add_room_labels(entities, tags, rooms)
      lbl_grp       = entities.add_group
      lbl_grp.layer = tags[:labels]
      lbl_grp.name  = 'Room Labels'
      le            = lbl_grp.entities

      rooms.each do |room|
        rname = room['name'] || room['id']
        rw    = room['width'].to_f
        rd    = room['depth'].to_f
        area  = (rw * rd).round
        cx    = (room['x'].to_f + rw / 2.0) * FT
        cy    = (room['y'].to_f + rd / 2.0) * FT
        pt    = Geom::Point3d.new(cx, cy, 0.1 * FT)
        le.add_text("#{rname}\n#{area} ft²", pt) rescue nil
      end
    end

    def self.set_camera(model, sw, sd, fh)
      camera = model.active_view.camera
      camera.set(
        Geom::Point3d.new(sw * 0.5 * FT, -sd * 0.8 * FT, fh * 1.8 * FT),
        Geom::Point3d.new(sw * 0.5 * FT,  sd * 0.5 * FT, 0),
        Geom::Vector3d.new(0, 0, 1)
      )
      model.active_view.zoom_extents
    end
  end
end
