import React, { useMemo } from "react";
import RegionSelect from "@/components/RegionSelect";
import { getDistrictsFor } from "@/lib/districts";

// District (tuman) picker: a searchable list for Uzbek regions; free text only
// where no list exists (other countries). Disabled until a region is chosen.
export default function DistrictSelect({ country, region, value, onChange, placeholder, testid = "district-select", disabledHint }) {
  const options = useMemo(() => getDistrictsFor(country, region), [country, region]);
  if (!region) {
    return (
      <div data-testid={`${testid}-disabled`} className="input text-muted-foreground opacity-70 select-none">
        {disabledHint || placeholder}
      </div>
    );
  }
  if (!options) {
    return (
      <input data-testid={testid} className="input" value={value || ""} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
    );
  }
  return <RegionSelect options={options} value={value || ""} onChange={onChange} placeholder={placeholder} testid={testid} emptyText="—" />;
}
