# Scotch MCP Chat Bridge — in-SketchUp AI design chat (Stage 25.7)
#
# Opens a simple HTML dialog connected to the Scotch chat endpoint
# (POST /projects/{id}/chat). After each AI turn that returns an updated
# project, the extension automatically triggers a sync pull so the SketchUp
# model stays in sync with the canonical model.
#
# Requires the Scotch backend running at api_base (default localhost:8000).
# Set SCOTCH_MCP_ENABLED=true in the model attributes to enable the menu item.

require 'json'

module ScotchImporter
  module McpChat
    def self.chat_html(project_id, api_base)
      <<~HTML
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <title>Scotch AI Chat</title>
          <style>
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, sans-serif; }
            body { display: flex; flex-direction: column; height: 100vh; background: #fafafa; }
            #header { background: #1a1a1a; color: #fff; padding: 10px 14px; font-size: 13px; font-weight: 600; }
            #header span { color: #a78bfa; }
            #thread { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px; }
            .msg { max-width: 88%; padding: 8px 12px; border-radius: 10px; font-size: 12px; line-height: 1.5; }
            .user { align-self: flex-end; background: #1a1a1a; color: #fff; }
            .assistant { align-self: flex-start; background: #ede9fe; color: #1a1a1a; }
            .pending { align-self: flex-start; background: #f3f4f6; color: #9ca3af; font-style: italic; }
            .tools { margin-top: 4px; display: flex; flex-wrap: wrap; gap: 4px; }
            .tool-badge { background: #7c3aed22; color: #6d28d9; padding: 2px 6px; border-radius: 4px; font-size: 10px; }
            #input-area { display: flex; gap: 6px; padding: 10px; border-top: 1px solid #e5e7eb; background: #fff; }
            #input { flex: 1; border: 1px solid #d1d5db; border-radius: 8px; padding: 7px 10px; font-size: 12px; resize: none; }
            #send { background: #1a1a1a; color: #fff; border: none; border-radius: 8px; padding: 8px 14px; font-size: 12px; cursor: pointer; }
            #send:disabled { opacity: 0.4; cursor: default; }
            #status { padding: 4px 10px; font-size: 10px; color: #6b7280; background: #f9fafb; border-top: 1px solid #f3f4f6; }
          </style>
        </head>
        <body>
          <div id="header">Scotch AI <span>● #{project_id}</span></div>
          <div id="thread"></div>
          <div id="input-area">
            <textarea id="input" rows="2" placeholder="Add a bedroom, make kitchen 10×12…"></textarea>
            <button id="send" onclick="send()">Send</button>
          </div>
          <div id="status">Ready</div>
          <script>
            const PROJECT_ID = '#{project_id}';
            const API_BASE   = '#{api_base}';
            let history = [];
            let busy = false;

            function addMsg(role, content, toolCalls) {
              const thread = document.getElementById('thread');
              const div = document.createElement('div');
              div.className = 'msg ' + (role === 'user' ? 'user' : 'assistant');
              div.textContent = content;
              if (toolCalls && toolCalls.length) {
                const tools = document.createElement('div');
                tools.className = 'tools';
                [...new Set(toolCalls)].forEach(tc => {
                  const b = document.createElement('span');
                  b.className = 'tool-badge';
                  b.textContent = tc.replace(/_/g, ' ');
                  tools.appendChild(b);
                });
                div.appendChild(tools);
              }
              thread.appendChild(div);
              thread.scrollTop = thread.scrollHeight;
              return div;
            }

            function setStatus(msg) {
              document.getElementById('status').textContent = msg;
            }

            async function send() {
              if (busy) return;
              const input = document.getElementById('input');
              const text = input.value.trim();
              if (!text) return;
              input.value = '';
              busy = true;
              document.getElementById('send').disabled = true;

              addMsg('user', text);
              const pending = addMsg('assistant', 'Thinking…');
              pending.className = 'msg pending';
              setStatus('Asking Scotch AI…');

              try {
                const resp = await fetch(API_BASE + '/projects/' + PROJECT_ID + '/chat', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ message: text, history }),
                });
                const data = await resp.json();
                pending.remove();
                addMsg('assistant', data.reply, data.tool_calls);
                history = [...history,
                  { role: 'user', content: text },
                  { role: 'assistant', content: data.reply }
                ].slice(-20);

                if (data.project) {
                  setStatus('Design updated — syncing model…');
                  window.location = 'sketchup:sync_pull_after_chat';
                } else {
                  setStatus('Ready');
                }
              } catch(e) {
                pending.remove();
                addMsg('assistant', 'Error: ' + e.message + ' — is the backend running?');
                setStatus('Error');
              } finally {
                busy = false;
                document.getElementById('send').disabled = false;
              }
            }

            document.getElementById('input').addEventListener('keydown', function(e) {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
            });
          </script>
        </body>
        </html>
      HTML
    end

    def self.run
      model = Sketchup.active_model
      project_id = model.get_attribute('ScotchProject', 'project_id', nil)
      api_base   = model.get_attribute('ScotchProject', 'api_base', 'http://localhost:8000')

      unless project_id
        result = UI.messagebox("No Scotch project linked to this model.\nEnter a project ID:", MB_OKCANCEL)
        return if result == IDCANCEL
        project_id = UI.inputbox(['Project ID'], [''], 'Link Scotch Project').first
        return unless project_id && !project_id.strip.empty?
        project_id = project_id.strip
        model.set_attribute('ScotchProject', 'project_id', project_id)
      end

      dlg = UI::HtmlDialog.new(
        dialog_title:    'Scotch AI Chat',
        preferences_key: 'scotch_ai_chat',
        scrollable:      false,
        resizable:       true,
        width:           380,
        height:          520,
        left:            200,
        top:             200,
        min_width:       320,
        min_height:      380,
      )
      dlg.set_html(chat_html(project_id, api_base))

      # When the dialog signals "sync_pull_after_chat", run a pull silently.
      dlg.add_action_callback('sync_pull_after_chat') do |_ctx, _params|
        ScotchImporter::SyncPull.run rescue nil
      end

      dlg.show
    end
  end
end
