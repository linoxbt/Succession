/**
 * The Succession Certificate.
 *
 * Every field is already produced upstream — this renders, it does not compute.
 * The download is a text file rather than a styled PDF: a document whose value
 * is "this hash matched that hash" gains nothing from typesetting.
 */
import type { Certificate as CertificateType } from "../api";
import { Button, Definition, DefinitionList, Section } from "./primitives";

export function Certificate({
  certificate,
  text,
}: {
  certificate: CertificateType;
  text: string;
}) {
  function download() {
    const body =
      text || `${JSON.stringify(certificate, null, 2)}\n`;
    const blob = new Blob([body], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `succession-certificate-${certificate.memory_asset.replace("#", "")}.txt`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Section title="Succession certificate">
      <div className="border border-rule p-6">
        <DefinitionList>
          <Definition label="Memory asset">{certificate.memory_asset}</Definition>
          <Definition label="Origin agent" mono>
            {certificate.origin_agent}
          </Definition>
          <Definition label="Successor agent" mono>
            {certificate.successor_agent}
          </Definition>
          <Definition label="Memory version">{certificate.memory_version}</Definition>
          <Definition label="Records transferred">
            {certificate.records_transferred.toLocaleString()}
          </Definition>
          <Definition label="Categories transferred">
            {certificate.categories_transferred.join(", ")}
          </Definition>
          <Definition label="Integrity hash" mono>
            {certificate.integrity_hash}
          </Definition>
          {certificate.seller_tenant_sealed_at ? (
            <Definition label="Origin tenant sealed" mono>
              {certificate.seller_tenant_sealed_at}
            </Definition>
          ) : null}
          <Definition label="Transfer date" mono>
            {certificate.transfer_date}
          </Definition>
          <Definition label="Transfer status">{certificate.transfer_status}</Definition>
        </DefinitionList>
      </div>
      <div className="mt-5">
        <Button tone="quiet" onClick={download}>
          Download certificate
        </Button>
      </div>
    </Section>
  );
}
