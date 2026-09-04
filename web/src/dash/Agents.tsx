/**
 * Virtuals ACP — the earnings record a buyer can check without the seller.
 *
 * Every figure on this screen resolves to an on-chain job id. That is the whole
 * reason it sits apart from the data room's own counts, which are computed from
 * the seller's memory and therefore self-reported.
 */
import type { Preview } from "../api";
import { Badge, Empty, Field, Panel, Stat, StatRow } from "../ui";

export function Agents({ preview }: { preview: Preview | null }) {
  const acp = preview?.acp;

  if (!acp) {
    return (
      <Panel title="Virtuals ACP">
        <Empty>
          No ACP job history on this agent. Register it through the ACP Tech
          Playbook, then run <code className="font-mono">succession-acp sync</code>.
        </Empty>
      </Panel>
    );
  }

  return (
    <div className="space-y-6">
      <Panel>
        <StatRow>
          <Stat label="Completed jobs" value={acp.completed_jobs} tone="good" />
          <Stat label="Failed or expired" value={acp.failed_jobs} />
          <Stat label="Gross volume" value={acp.gross_volume} sub="USDC" />
          <Stat
            label="Success rate"
            value={acp.success_rate ? `${(Number(acp.success_rate) * 100).toFixed(0)}%` : "—"}
            sub={acp.success_rate ? "Feeds the valuation" : "Sample too small"}
          />
        </StatRow>
      </Panel>

      <Panel title="Registration">
        <dl>
          <Field label="Status">
            <Badge tone={acp.registered ? "good" : "bad"}>
              {acp.registered ? "On the service registry" : "Not registered"}
            </Badge>
          </Field>
          <Field label="Agent">{acp.agent_name || "—"}</Field>
          <Field label="Entity id">
            <span className="font-mono">{acp.agent_id ?? "—"}</span>
          </Field>
          <Field label="Wallet">
            <span className="font-mono break-all">{acp.agent_address || "—"}</span>
          </Field>
          <Field label="Counterparties">{acp.distinct_counterparties}</Field>
          <Field label="Source">
            <Badge tone={acp.source === "live" ? "good" : "neutral"}>{acp.source}</Badge>
          </Field>
        </dl>
      </Panel>

      <Panel
        title="Verifiable job ids"
        action={<span className="text-xs text-faint">Resolve against the ACP contract</span>}
      >
        <div className="flex flex-wrap gap-1.5 px-5 py-4">
          {acp.verifiable_job_ids.map((id) => (
            <span
              key={id}
              className="rounded border border-line px-2 py-0.5 font-mono text-[0.75rem] tnum text-secondary"
            >
              #{id}
            </span>
          ))}
        </div>
        <p className="border-t border-hairline px-5 py-3 text-xs text-faint">
          {acp.verification}
        </p>
      </Panel>
    </div>
  );
}
