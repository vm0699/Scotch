import { AppShell } from "@/components/layout/app-shell";
import { Workspace } from "@/components/workspace/workspace";

export default async function WorkspacePage({
  searchParams,
}: {
  searchParams: Promise<{ template?: string }>;
}) {
  const { template } = await searchParams;

  return (
    <AppShell active="/workspace">
      <Workspace initialTemplateId={template} />
    </AppShell>
  );
}
