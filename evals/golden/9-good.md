The training image lacks UseCompactObjectHeaders, so the AOT cache will be rejected: a parity mismatch. Add the AOTMode gate (required on 27) in the build so the acceptance check fails loudly.
