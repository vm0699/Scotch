# Scotch Sync Push — send SketchUp edits back to the canonical model (Stage 25.4)
#
# Traverses all groups on the S-ROOMS tag, reads their current bounding-box
# position and size, builds a SyncPayload, and POSTs it to the Scotch API.
#
# Room group names must follow the convention established by builder.rb:
#   "Room Name [room_id]"
#
# The result dialog shows a diff summary and any conflict warnings.

require 'json'

module ScotchImporter
  module SyncPush
    FT = 12.0  # SketchUp inches per foot — same as Builder::FT

    # Extract the stable room id from a group name like "Kitchen [kit-1]"
    def self.parse_room_id(group_name)
      return nil unless group_name
      m = group_name.match(/\[([^\]]+)\]\s*$/)
      m ? m[1] : nil
    end

    # Extract the room name (the text before the bracketed id)
    def self.parse_room_name(group_name)
      return group_name unless group_name
      group_name.sub(/\s*\[[^\]]+\]\s*$/, '').strip
    end

    # Convert a SketchUp BoundingBox into SyncRoom geometry (feet)
    def self.bbox_to_room(bbox)
      min_pt = bbox.min
      max_pt = bbox.max
      x = min_pt.x / FT
      y = min_pt.y / FT
      w = (max_pt.x - min_pt.x) / FT
      d = (max_pt.y - min_pt.y) / FT
      [x, y, w, d]
    end

    # Collect all room groups from the active model's S-ROOMS layer
    def self.collect_rooms(model)
      rooms = []
      model.entities.each do |ent|
        next unless ent.is_a?(Sketchup::Group)
        next unless ent.layer&.name == 'S-ROOMS'

        rid = parse_room_id(ent.name)
        next unless rid

        rname = parse_room_name(ent.name)
        x, y, w, d = bbox_to_room(ent.bounds)
        next if w < 0.1 || d < 0.1  # degenerate / collapsed groups

        # level is encoded in the group's elevation (z / floor_height)
        fh_attr = model.get_attribute('ScotchProject', 'floor_height', 10.0).to_f
        z_center = ent.bounds.center.z / FT
        level = fh_attr > 0 ? [0, (z_center / fh_attr).round].max : 0

        rooms << {
          'id'    => rid,
          'name'  => rname,
          'type'  => 'bedroom',  # type is not stored in geometry; use 'bedroom' as default
          'x'     => x.round(2),
          'y'     => y.round(2),
          'width' => w.round(2),
          'depth' => d.round(2),
          'level' => level,
        }
      end
      rooms
    end

    # POST the payload to the Scotch API and return the parsed response Hash
    def self.post_sync(api_base, project_id, rooms)
      require 'net/http'
      require 'uri'

      uri = URI("#{api_base}/projects/#{project_id}/sync")
      body = JSON.generate({ 'rooms' => rooms, 'source' => 'sketchup' })

      http = Net::HTTP.new(uri.host, uri.port)
      http.use_ssl = uri.scheme == 'https'
      http.open_timeout = 10
      http.read_timeout = 30

      req = Net::HTTP::Post.new(uri.path, 'Content-Type' => 'application/json')
      req.body = body
      resp = http.request(req)

      unless resp.is_a?(Net::HTTPSuccess)
        raise "API error #{resp.code}: #{resp.body}"
      end

      JSON.parse(resp.body)
    end

    # Build and show a human-readable diff summary
    def self.diff_message(diff)
      lines = []
      lines << "✓ Sync to Scotch complete.\n"
      lines << "  Added:   #{diff['added'].length} room(s)"   unless diff['added'].empty?
      lines << "  Updated: #{diff['updated'].length} room(s)" unless diff['updated'].empty?
      lines << "  Flagged: #{diff['flagged'].length} room(s) only in Scotch (not deleted)" unless diff['flagged'].empty?
      if diff['conflicts'] && !diff['conflicts'].empty?
        lines << "\n⚠ Large dimensional changes detected:"
        diff['conflicts'].each do |c|
          lines << "  #{c['room_name']} (#{c['room_id']}) — #{c['field']}: " \
                   "#{c['scotch_value'].round(2)} ft → #{c['incoming_value'].round(2)} ft " \
                   "(Δ #{c['delta'].round(2)} ft)"
        end
        lines << "\nThese were applied. Restore a previous version in Scotch if unintended."
      end
      lines.join("\n")
    end

    # Main entry point
    def self.run
      model = Sketchup.active_model
      project_id = model.get_attribute('ScotchProject', 'project_id', nil)
      api_base   = model.get_attribute('ScotchProject', 'api_base', 'http://localhost:8000')

      unless project_id
        result = UI.messagebox(
          "No Scotch project linked to this model.\n\n" \
          "Enter a project ID (copy from the Scotch web app URL):",
          MB_OKCANCEL
        )
        return if result == IDCANCEL
        project_id = UI.inputbox(['Project ID'], [''], 'Link Scotch Project').first
        return unless project_id && !project_id.strip.empty?
        project_id = project_id.strip
        model.set_attribute('ScotchProject', 'project_id', project_id)
      end

      rooms = collect_rooms(model)
      if rooms.empty?
        UI.messagebox("No Scotch room groups found on the S-ROOMS tag.\n\nImport a design first, or ensure your groups are on the S-ROOMS tag.")
        return
      end

      begin
        diff = post_sync(api_base, project_id, rooms)
        UI.messagebox(diff_message(diff))
      rescue => e
        UI.messagebox("Sync failed:\n#{e.message}\n\nIs the Scotch backend running at #{api_base}?")
      end
    end
  end
end
