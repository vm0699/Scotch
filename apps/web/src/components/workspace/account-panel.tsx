"use client";

/**
 * Phase 37 — Account / Profile panel.
 *
 * Shows local account mode with a sign-in-ready placeholder for future
 * Google OAuth. Displays and edits the architect-twin UserProfile.
 */

import { Cloud, CloudOff, Pencil, User } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { PanelSection } from "@/components/layout/panel";
import { Button } from "@/components/ui/button";
import { getUserProfile, updateUserProfile, type UserProfile } from "@/features/api/client";

// ── Account mode badge ────────────────────────────────────────────────────────

function AccountModeBadge({ mode }: { mode: "local" | "cloud" }) {
  const isCloud = mode === "cloud";
  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
      isCloud
        ? "bg-blue-50 text-blue-700 border-blue-200"
        : "bg-stone-50 text-stone-600 border-stone-200"
    }`}>
      {isCloud ? <Cloud className="w-3 h-3" /> : <CloudOff className="w-3 h-3" />}
      {isCloud ? "Cloud account" : "Local account"}
    </div>
  );
}

// ── Sign-in placeholder ───────────────────────────────────────────────────────

function SignInPlaceholder() {
  return (
    <div className="rounded-lg border border-dashed border-stone-200 bg-stone-50/50 p-4 text-center space-y-2">
      <Cloud className="w-6 h-6 mx-auto text-stone-400" />
      <p className="text-xs text-muted-foreground font-medium">
        Sign in with Google to sync projects across devices
      </p>
      <Button
        size="sm"
        variant="outline"
        disabled
        className="w-full text-xs text-stone-500 border-stone-200"
      >
        Sign in with Google — coming soon
      </Button>
      <p className="text-[10px] text-stone-400">
        Local mode works without an account. All data stays on this machine.
      </p>
    </div>
  );
}

// ── Profile editor ────────────────────────────────────────────────────────────

type EditableProfile = Pick<
  UserProfile,
  "display_name" | "role" | "preferred_units" | "default_location" | "default_style" | "explanation_style"
>;

function ProfileEditor({
  profile,
  onSaved,
}: {
  profile: UserProfile;
  onSaved: (p: UserProfile) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<EditableProfile>({
    display_name: profile.display_name,
    role: profile.role,
    preferred_units: profile.preferred_units,
    default_location: profile.default_location,
    default_style: profile.default_style,
    explanation_style: profile.explanation_style,
  });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await updateUserProfile(form);
      onSaved(updated);
      setEditing(false);
      toast.success("Profile saved");
    } catch {
      toast.error("Failed to save profile");
    } finally {
      setSaving(false);
    }
  };

  if (!editing) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-stone-200 flex items-center justify-center">
              <User className="w-3.5 h-3.5 text-stone-500" />
            </div>
            <div>
              <p className="text-xs font-semibold text-foreground leading-tight">
                {profile.display_name || "Architect"}
              </p>
              <p className="text-[10px] text-muted-foreground capitalize">{profile.role}</p>
            </div>
          </div>
          <Button
            size="sm"
            variant="ghost"
            className="h-6 px-2 text-xs text-muted-foreground"
            onClick={() => setEditing(true)}
          >
            <Pencil className="w-3 h-3 mr-1" />
            Edit
          </Button>
        </div>

        <div className="grid grid-cols-2 gap-1.5 text-[10px]">
          <div className="rounded border border-stone-100 bg-stone-50 px-2 py-1">
            <span className="text-muted-foreground">Units</span>
            <p className="font-medium capitalize">{profile.preferred_units}</p>
          </div>
          <div className="rounded border border-stone-100 bg-stone-50 px-2 py-1">
            <span className="text-muted-foreground">Location</span>
            <p className="font-medium truncate">{profile.default_location || "India"}</p>
          </div>
          <div className="rounded border border-stone-100 bg-stone-50 px-2 py-1">
            <span className="text-muted-foreground">Style</span>
            <p className="font-medium truncate">{profile.default_style || "modern"}</p>
          </div>
          <div className="rounded border border-stone-100 bg-stone-50 px-2 py-1">
            <span className="text-muted-foreground">Explanations</span>
            <p className="font-medium capitalize">{profile.explanation_style}</p>
          </div>
        </div>
      </div>
    );
  }

  const labelCls = "block text-[10px] font-medium text-muted-foreground mb-0.5";
  const inputCls = "w-full text-xs border border-stone-200 rounded px-2 py-1 bg-background focus:outline-none focus:ring-1 focus:ring-stone-400";

  return (
    <div className="space-y-2">
      <div>
        <label className={labelCls}>Display name</label>
        <input
          className={inputCls}
          value={form.display_name}
          onChange={(e) => setForm({ ...form, display_name: e.target.value })}
          placeholder="Your name"
        />
      </div>

      <div>
        <label className={labelCls}>Role</label>
        <select
          className={inputCls}
          value={form.role}
          onChange={(e) => setForm({ ...form, role: e.target.value as UserProfile["role"] })}
        >
          <option value="architect">Architect</option>
          <option value="owner">Owner / Developer</option>
          <option value="student">Student</option>
          <option value="other">Other</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className={labelCls}>Units</label>
          <select
            className={inputCls}
            value={form.preferred_units}
            onChange={(e) => setForm({ ...form, preferred_units: e.target.value as "feet" | "meters" })}
          >
            <option value="feet">Feet</option>
            <option value="meters">Meters</option>
          </select>
        </div>
        <div>
          <label className={labelCls}>Explanations</label>
          <select
            className={inputCls}
            value={form.explanation_style}
            onChange={(e) => setForm({ ...form, explanation_style: e.target.value as "brief" | "detailed" })}
          >
            <option value="brief">Brief</option>
            <option value="detailed">Detailed</option>
          </select>
        </div>
      </div>

      <div>
        <label className={labelCls}>Default location</label>
        <input
          className={inputCls}
          value={form.default_location}
          onChange={(e) => setForm({ ...form, default_location: e.target.value })}
          placeholder="e.g. Tamil Nadu, India"
        />
      </div>

      <div>
        <label className={labelCls}>Default style</label>
        <input
          className={inputCls}
          value={form.default_style}
          onChange={(e) => setForm({ ...form, default_style: e.target.value })}
          placeholder="e.g. modern minimal"
        />
      </div>

      <div className="flex gap-2 pt-1">
        <Button size="sm" className="flex-1 h-7 text-xs" onClick={handleSave} disabled={saving}>
          {saving ? "Saving…" : "Save profile"}
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-xs"
          onClick={() => setEditing(false)}
          disabled={saving}
        >
          Cancel
        </Button>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function AccountPanel() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const ctrl = new AbortController();
    getUserProfile(ctrl.signal)
      .then(setProfile)
      .catch(() => {/* backend not running */})
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, []);

  if (loading) {
    return (
      <PanelSection title="Account">
        <div className="space-y-2 animate-pulse">
          <div className="h-8 bg-stone-100 rounded" />
          <div className="h-4 bg-stone-100 rounded w-2/3" />
        </div>
      </PanelSection>
    );
  }

  return (
    <PanelSection title="Account">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <AccountModeBadge mode={profile?.account_mode ?? "local"} />
          {profile?.cloud_email && (
            <span className="text-[10px] text-muted-foreground truncate max-w-[120px]">
              {profile.cloud_email}
            </span>
          )}
        </div>

        {profile ? (
          <ProfileEditor profile={profile} onSaved={setProfile} />
        ) : (
          <p className="text-xs text-muted-foreground">Profile unavailable — backend offline.</p>
        )}

        {(!profile || profile.account_mode === "local") && <SignInPlaceholder />}
      </div>
    </PanelSection>
  );
}
