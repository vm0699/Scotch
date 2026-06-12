import { AppShell } from "@/components/layout/app-shell";
import { Workspace } from "@/components/workspace/workspace";

export default async function WorkspacePage({
  searchParams,
}: {
  searchParams: Promise<{ template?: string; project?: string }>;
}) {
  const { template, project } = await searchParams;

  return (
    <AppShell active="/workspace">
      <Workspace initialTemplateId={template} initialProjectId={project} />
    </AppShell>
  );
}
