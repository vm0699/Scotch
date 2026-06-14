# Scotch Importer — main loader
# Loaded by scotch_importer.rb via SketchupExtension.

require 'sketchup'
require File.join(__dir__, 'importer')
require File.join(__dir__, 'builder')

module ScotchImporter
  unless file_loaded?(__FILE__)
    # ── Menu item ────────────────────────────────────────────────────────────
    ext_menu = UI.menu('Extensions')
    scotch_menu = ext_menu.add_submenu('Scotch')
    scotch_menu.add_item('Import Design…') { ScotchImporter.import_design }
    scotch_menu.add_item('About Scotch Importer') { ScotchImporter.show_about }

    # ── Toolbar ──────────────────────────────────────────────────────────────
    toolbar = UI::Toolbar.new('Scotch')

    cmd_import = UI::Command.new('Import Scotch Design') { ScotchImporter.import_design }
    cmd_import.tooltip     = 'Import a Scotch architecture project.json'
    cmd_import.status_bar_text = 'Open a Scotch project.json file and build the 3D model.'
    toolbar.add_item(cmd_import)
    toolbar.restore

    file_loaded(__FILE__)
  end

  def self.import_design
    path = ScotchImporter::Importer.pick_file
    return unless path

    data = ScotchImporter::Importer.load_json(path)
    return unless data

    ScotchImporter::Builder.build(data)
    UI.messagebox("Scotch design \"#{data['name']}\" imported successfully!\n\n" \
                  "• Room groups are named <Room> [id] in the Outliner.\n" \
                  "• Toggle S-LABELS to show/hide room labels.\n" \
                  "• Use Tags panel to control layer visibility.")
  rescue => e
    UI.messagebox("Error importing Scotch design:\n#{e.message}\n\n#{e.backtrace.first(3).join("\n")}")
  end

  def self.show_about
    UI.messagebox("Scotch Importer v#{ScotchImporter::EXTENSION.version}\n\n" \
                  "Imports Scotch architecture designs (project.json) into SketchUp.\n\n" \
                  "Export a project.json from Scotch, then use\n" \
                  "Extensions > Scotch > Import Design.\n\n" \
                  "Tags: S-SITE · S-ROOMS · S-ROOF · S-LABELS · S-OPENINGS")
  end
end
