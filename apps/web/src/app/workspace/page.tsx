import { AppShell } from "@/components/layout/app-shell";
import {
  Panel,
  PanelBody,
  PanelEmpty,
  PanelHeader,
} from "@/components/layout/panel";
import { StatusBadge } from "@/components/layout/status-badge";

export default function WorkspacePage() {
  return (
    <AppShell active="/workspace">
      <div className="grid h-full grid-cols-1 gap-3 p-3 lg:grid-cols-[300px_minmax(0,1fr)_340px]">
        <Panel>
          <PanelHeader
            title="Design Brief"
            actions={<StatusBadge variant="info">Deterministic</StatusBadge>}
          />
          <PanelBody className="flex flex-col">
            <PanelEmpty>
              Prompt input, templates, and the Generate button land in Stage
              2.3.
            </PanelEmpty>
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader title="Preview" />
          <PanelBody className="flex flex-col">
            <PanelEmpty>
              2D floor plan canvas and 3D massing tab land in Stages 2.3–2.5.
            </PanelEmpty>
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader title="Design Data" />
          <PanelBody className="flex flex-col">
            <PanelEmpty>
              Parameter editor, room schedule, exports, and warnings land in
              Stage 2.3.
            </PanelEmpty>
          </PanelBody>
        </Panel>
      </div>
    </AppShell>
  );
}
