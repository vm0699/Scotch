# Scotch Sync Pull — update SketchUp groups from the canonical model (Stage 25.5)
#
# GETs GET /projects/{id}/sync, compares the SyncContract with the current
# SketchUp model, and moves/resizes room groups to match Scotch.
#
# Only moves/resizes existing groups — does NOT rebuild geometry or delete
# rooms. Extra detail the architect added in SketchUp is preserved.

require 'json'

module ScotchImporter
  module SyncPull
    FT = 12.0

    # Fetch the SyncContract from the Scotch API
    def self.fetch_contract(api_base, project_id)
      require 'net/http'
      require 'uri'

      uri = URI("#{api_base}/projects/#{project_id}/sync")
      http = Net::HTTP.new(uri.host, uri.port)
      http.use_ssl = uri.scheme == 'https'
      http.open_timeout = 10
      http.read_timeout = 30

      req = Net::HTTP::Get.new(uri.path, 'Accept' => 'application/json')
      resp = http.request(req)

      unless resp.is_a?(Net::HTTPSuccess)
        raise "API error #{resp.code}: #{resp.body}"
      end

      JSON.parse(resp.body)
    end

    # Find all room groups indexed by room id
    def self.room_groups(model)
      groups = {}
      model.entities.each do |ent|
        next unless ent.is_a?(Sketchup::Group)
        next unless ent.layer&.name == 'S-ROOMS'
        rid = ScotchImporter::SyncPush.parse_room_id(ent.name)
        groups[rid] = ent if rid
      end
      groups
    end

    # Compute the transform needed to move/scale a group to match a SyncRoom
    def self.move_group_to(grp, sr)
      bbox = grp.bounds
      min_pt = bbox.min

      # Translation delta in inches
      dx = sr['x'].to_f * FT - min_pt.x
      dy = sr['y'].to_f * FT - min_pt.y
      dz = 0.0

      tr = Geom::Transformation.translation(Geom::Vector3d.new(dx, dy, dz))
      grp.transform!(tr)
    end

    # Main entry point
    def self.run
      model = Sketchup.active_model
      project_id = model.get_attribute('ScotchProject', 'project_id', nil)
      api_base   = model.get_attribute('ScotchProject', 'api_base', 'http://localhost:8000')

      unless project_id
        result = UI.messagebox(
          "No Scotch project linked to this model.\n\nEnter a project ID:",
          MB_OKCANCEL
        )
        return if result == IDCANCEL
        project_id = UI.inputbox(['Project ID'], [''], 'Link Scotch Project').first
        return unless project_id && !project_id.strip.empty?
        project_id = project_id.strip
        model.set_attribute('ScotchProject', 'project_id', project_id)
      end

      begin
        contract = fetch_contract(api_base, project_id)
      rescue => e
        UI.messagebox("Pull failed:\n#{e.message}\n\nIs the Scotch backend running at #{api_base}?")
        return
      end

      rooms = contract['rooms'] || []
      if rooms.empty?
        UI.messagebox("Scotch returned an empty room list — nothing to pull.")
        return
      end

      groups = room_groups(model)
      moved = 0
      skipped = []

      model.start_operation('Scotch Sync Pull', true)
      rooms.each do |sr|
        rid = sr['id']
        grp = groups[rid]
        if grp
          begin
            move_group_to(grp, sr)
            moved += 1
          rescue => e
            skipped << "#{sr['name']} (#{rid}): #{e.message}"
          end
        else
          skipped << "#{sr['name']} (#{rid}): not found in model (import first)"
        end
      end
      model.commit_operation

      msg = "Scotch Sync Pull complete.\n\nMoved/updated #{moved} room group(s)."
      unless skipped.empty?
        msg += "\n\nSkipped #{skipped.length} room(s):\n" + skipped.join("\n")
      end
      UI.messagebox(msg)
    end
  end
end
