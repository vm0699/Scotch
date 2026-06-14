# Scotch Importer — SketchUp Extension Registration
# Version: 1.0.0
#
# Install: copy this file and the scotch/ folder to your SketchUp Plugins directory.
#   macOS:   ~/Library/Application Support/SketchUp <version>/SketchUp/Plugins/
#   Windows: %APPDATA%\SketchUp\SketchUp <version>\SketchUp\Plugins\
#
# After copying, restart SketchUp and enable the extension in
# Window > Extension Manager.
#
# Usage: Extensions > Scotch: Import Design

require 'sketchup'
require 'extensions'

module ScotchImporter
  EXTENSION = SketchupExtension.new('Scotch Importer', 'scotch/main')
  EXTENSION.version     = '1.0.0'
  EXTENSION.copyright   = '2026 Scotch'
  EXTENSION.creator     = 'Scotch'
  EXTENSION.description = 'Import Scotch architecture designs (project.json) ' \
                          'into SketchUp as grouped, tagged, material-applied 3D models.'

  Sketchup.register_extension(EXTENSION, true)
end
