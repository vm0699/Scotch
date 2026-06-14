# Scotch Importer — JSON file picker and parser (Stage 15.3)
#
# Responsibilities:
#   1. Open a file-picker dialog filtered to .json files.
#   2. Read and JSON-parse the chosen file.
#   3. Validate required top-level keys; surface a messagebox on malformed input.
#   4. Return the parsed Ruby Hash, or nil on any failure.

require 'json'

module ScotchImporter
  module Importer
    # Keys every valid Scotch project.json must contain.
    REQUIRED_KEYS = %w[id name rooms site building].freeze

    # Open a platform-native file picker and return the chosen path (or nil if
    # the user cancelled).
    def self.pick_file
      path = UI.openpanel(
        'Open Scotch Project JSON',
        '',
        'JSON Files|*.json||All Files|*.*||'
      )
      # UI.openpanel returns nil or "" on cancel depending on platform.
      return nil if path.nil? || path.strip.empty?
      path.strip
    end

    # Read *path*, parse it as JSON, validate required keys, and return the
    # Hash.  Returns nil and shows a messagebox on any error.
    def self.load_json(path)
      unless File.exist?(path)
        UI.messagebox("File not found:\n#{path}")
        return nil
      end

      raw = File.read(path, encoding: 'UTF-8')

      data = JSON.parse(raw)

      missing = REQUIRED_KEYS.reject { |k| data.key?(k) }
      unless missing.empty?
        UI.messagebox(
          "Invalid Scotch project file.\n\n" \
          "Missing required keys: #{missing.join(', ')}\n\n" \
          "Please export a fresh project.json from Scotch."
        )
        return nil
      end

      # Validate rooms is a non-empty array
      unless data['rooms'].is_a?(Array) && !data['rooms'].empty?
        UI.messagebox("Project contains no rooms — nothing to import.")
        return nil
      end

      data

    rescue JSON::ParserError => e
      UI.messagebox("Failed to parse JSON file:\n#{e.message}\n\nIs this a valid Scotch project.json?")
      nil
    rescue Errno::ENOENT => e
      UI.messagebox("Cannot read file:\n#{e.message}")
      nil
    rescue => e
      UI.messagebox("Unexpected error reading file:\n#{e.message}")
      nil
    end
  end
end
