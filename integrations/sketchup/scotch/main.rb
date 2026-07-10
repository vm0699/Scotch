# Scotch Importer — main loader
# Loaded by scotch_importer.rb via SketchupExtension.

require 'sketchup'
require File.join(__dir__, 'importer')
require File.join(__dir__, 'builder')
require File.join(__dir__, 'sync_push')
require File.join(__dir__, 'sync_pull')
require File.join(__dir__, 'mcp_chat')

module ScotchImporter
  unless file_loaded?(__FILE__)
    # ── Menu ─────────────────────────────────────────────────────────────────
    ext_menu   = UI.menu('Extensions')
    scotch_menu = ext_menu.add_submenu('Scotch')

    scotch_menu.add_item('Import Design…') { ScotchImporter.import_design }
    scotch_menu.add_separator
    scotch_menu.add_item('Sync ↑ to Scotch')   { ScotchImporter.sync_push }
    scotch_menu.add_item('Sync ↓ from Scotch') { ScotchImporter.sync_pull }
    scotch_menu.add_separator
    scotch_menu.add_item('AI Chat…')            { ScotchImporter.ai_chat }
    scotch_menu.add_separator
    scotch_menu.add_item('Set Project ID…')     { ScotchImporter.set_project_id }
    scotch_menu.add_item('About Scotch')        { ScotchImporter.show_about }

    # ── Toolbar ───────────────────────────────────────────────────────────────
    toolbar = UI::Toolbar.new('Scotch')

    cmd_import = UI::Command.new('Import Scotch Design') { ScotchImporter.import_design }
    cmd_import.tooltip          = 'Import a Scotch architecture project.json'
    cmd_import.status_bar_text  = 'Open a Scotch project.json file and build the 3D model.'
    toolbar.add_item(cmd_import)

    cmd_push = UI::Command.new('Sync ↑ to Scotch') { ScotchImporter.sync_push }
    cmd_push.tooltip         = 'Send your SketchUp edits back to Scotch'
    cmd_push.status_bar_text = 'Push room geometry changes from SketchUp into the Scotch canonical model.'
    toolbar.add_item(cmd_push)

    cmd_pull = UI::Command.new('Sync ↓ from Scotch') { ScotchImporter.sync_pull }
    cmd_pull.tooltip         = 'Update SketchUp from the latest Scotch design'
    cmd_pull.status_bar_text = 'Pull the current Scotch room layout into this SketchUp model.'
    toolbar.add_item(cmd_pull)

    cmd_chat = UI::Command.new('AI Chat') { ScotchImporter.ai_chat }
    cmd_chat.tooltip         = 'Chat with Scotch AI inside SketchUp'
    cmd_chat.status_bar_text = 'Open the Scotch AI chat dialog — design by conversation.'
    toolbar.add_item(cmd_chat)

    toolbar.restore
    file_loaded(__FILE__)
  end

  # ── Actions ────────────────────────────────────────────────────────────────

  def self.import_design
    path = ScotchImporter::Importer.pick_file
    return unless path
    data = ScotchImporter::Importer.load_json(path)
    return unless data
    ScotchImporter::Builder.build(data)
    UI.messagebox(
      "Scotch design \"#{data['name']}\" imported successfully!\n\n" \
      "• Room groups are named <Room> [id] in the Outliner.\n" \
      "• Toggle S-LABELS to show/hide room labels.\n" \
      "• Use Tags panel to control layer visibility."
    )
  rescue => e
    UI.messagebox("Error importing:\n#{e.message}\n\n#{e.backtrace.first(3).join("\n")}")
  end

  def self.sync_push
    ScotchImporter::SyncPush.run
  rescue => e
    UI.messagebox("Sync push error:\n#{e.message}")
  end

  def self.sync_pull
    ScotchImporter::SyncPull.run
  rescue => e
    UI.messagebox("Sync pull error:\n#{e.message}")
  end

  def self.ai_chat
    ScotchImporter::McpChat.run
  rescue => e
    UI.messagebox("AI chat error:\n#{e.message}")
  end

  def self.set_project_id
    model = Sketchup.active_model
    current_id  = model.get_attribute('ScotchProject', 'project_id', '')
    current_url = model.get_attribute('ScotchProject', 'api_base', 'http://localhost:8000')
    results = UI.inputbox(
      ['Project ID', 'API base URL'],
      [current_id, current_url],
      'Scotch Project Settings'
    )
    return unless results
    model.set_attribute('ScotchProject', 'project_id', results[0].strip) unless results[0].strip.empty?
    model.set_attribute('ScotchProject', 'api_base',   results[1].strip) unless results[1].strip.empty?
    UI.messagebox("Settings saved.\n\nProject ID: #{model.get_attribute('ScotchProject', 'project_id', '—')}")
  end

  def self.show_about
    UI.messagebox(
      "Scotch v#{ScotchImporter::EXTENSION.version}\n\n" \
      "Text-to-design for architecture.\n\n" \
      "Commands:\n" \
      "  Import Design — load a project.json from Scotch\n" \
      "  Sync ↑ to Scotch — push SketchUp edits → canonical model\n" \
      "  Sync ↓ from Scotch — pull latest design → SketchUp model\n" \
      "  AI Chat — design by conversation inside SketchUp\n" \
      "  Set Project ID — link this model to a Scotch project\n\n" \
      "Tags: S-SITE · S-ROOMS · S-ROOF · S-LABELS · S-OPENINGS"
    )
  end
end
