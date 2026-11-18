# BioCred M5 QA — adversarial probe of the anonymous surface.
#
# Runs with nothing but the publishable key that ships in the browser, i.e. the
# position of any stranger who reads the page source. Every probe states what it
# expects, so a run reads as a verdict rather than a dump.

$ErrorActionPreference = "Stop"
$base = "https://wmwzqnzyhiyhfzncuxkc.supabase.co"
$anon = "sb_publishable_sWwmE6Hyd_qZAmdHjgWLBg_ZQJAI1ks"
$H = @{ apikey = $anon; Authorization = "Bearer $anon" }

$results = @()

function Probe {
    param(
        [string]$Name,
        [string]$Expect,
        [scriptblock]$Call,
        [scriptblock]$Verdict
    )
    $out = $null; $status = $null; $err = $null
    try {
        $out = & $Call
        $status = 200
    } catch {
        $err = $_
        if ($_.Exception.Response) { $status = [int]$_.Exception.Response.StatusCode }
        try {
            $reader = New-Object IO.StreamReader($_.Exception.Response.GetResponseStream())
            $out = $reader.ReadToEnd() | ConvertFrom-Json
        } catch {}
    }
    $pass = & $Verdict $out $status
    $script:results += [pscustomobject]@{
        Probe  = $Name
        Expect = $Expect
        Status = $status
        Result = $(if ($pass) { "PASS" } else { "FAIL" })
        Saw    = $(if ($out -is [array]) { "$($out.Count) row(s)" } elseif ($out.message) { $out.message } elseif ($out.code) { $out.code } else { "$out" })
    }
}

function Get-Rest { param($path) Invoke-RestMethod -Uri "$base/rest/v1/$path" -Headers $H -Method GET }
function Post-Rpc { param($fn, $body) Invoke-RestMethod -Uri "$base/rest/v1/rpc/$fn" -Headers $H -Method POST -ContentType "application/json" -Body ($body | ConvertTo-Json) }

# ── 1. Base tables must not be readable row-by-row by a stranger ──────────────
Probe "read biologist_profile" "no rows / denied" `
    { Get-Rest "biologist_profile?select=id,full_name,verification_status" } `
    { param($o,$s) ($s -ne 200) -or ($o.Count -eq 0) }

Probe "read credential_record (doc paths)" "no rows / denied" `
    { Get-Rest "credential_record?select=id,documentation_url" } `
    { param($o,$s) ($s -ne 200) -or ($o.Count -eq 0) }

Probe "read experience_evidence" "no rows / denied" `
    { Get-Rest "experience_evidence?select=id,profile_id" } `
    { param($o,$s) ($s -ne 200) -or ($o.Count -eq 0) }

Probe "read verification_audit_log" "denied" `
    { Get-Rest "verification_audit_log?select=id,change_reason" } `
    { param($o,$s) ($s -ne 200) -or ($o.Count -eq 0) }

Probe "read user_roles" "denied" `
    { Get-Rest "user_roles?select=user_id,role" } `
    { param($o,$s) ($s -ne 200) -or ($o.Count -eq 0) }

# ── 2. Writes must be impossible ─────────────────────────────────────────────
Probe "insert biologist_profile" "denied" `
    { Invoke-RestMethod -Uri "$base/rest/v1/biologist_profile" -Headers $H -Method POST -ContentType "application/json" -Body '{"full_name":"QA Intruder"}' } `
    { param($o,$s) $s -ne 200 -and $s -ne 201 }

Probe "insert user_roles (self-promote)" "denied" `
    { Invoke-RestMethod -Uri "$base/rest/v1/user_roles" -Headers $H -Method POST -ContentType "application/json" -Body '{"role":"admin"}' } `
    { param($o,$s) $s -ne 200 -and $s -ne 201 }

Probe "insert verification_audit_log" "denied" `
    { Invoke-RestMethod -Uri "$base/rest/v1/verification_audit_log" -Headers $H -Method POST -ContentType "application/json" -Body '{"new_status":"verified","changed_by":"system"}' } `
    { param($o,$s) $s -ne 200 -and $s -ne 201 }

# ── 3. Privileged RPCs must refuse an anonymous caller ───────────────────────
Probe "rpc grant_role_by_email" "denied" `
    { Post-Rpc "grant_role_by_email" @{ p_email = "qa@example.com"; p_role = "admin" } } `
    { param($o,$s) $s -ne 200 }

Probe "rpc review_decide" "denied" `
    { Post-Rpc "review_decide" @{ p_profile_id = "00000000-0000-0000-0000-000000000000"; p_decision = "verified"; p_reason = "qa" } } `
    { param($o,$s) $s -ne 200 }

Probe "rpc review_start" "denied" `
    { Post-Rpc "review_start" @{ p_profile_id = "00000000-0000-0000-0000-000000000000" } } `
    { param($o,$s) $s -ne 200 }

Probe "rpc submit_profile_for_review" "denied" `
    { Post-Rpc "submit_profile_for_review" @{ p_profile_id = "00000000-0000-0000-0000-000000000000" } } `
    { param($o,$s) $s -ne 200 }

Probe "rpc is_reviewer_or_admin" "false or denied" `
    { Post-Rpc "is_reviewer_or_admin" @{} } `
    { param($o,$s) ($s -ne 200) -or ($o -eq $false) }

# ── 4. Public views must expose approved profiles only ───────────────────────
Probe "public view hides unapproved (PEND99)" "PEND99 absent" `
    { Get-Rest "profile_public_v1?select=registry_id" } `
    { param($o,$s) ($s -eq 200) -and (-not ($o.registry_id -contains "PEND99")) }

Probe "public view returns the approved one (SM7523)" "SM7523 present" `
    { Get-Rest "profile_public_v1?select=registry_id" } `
    { param($o,$s) ($s -eq 200) -and ($o.registry_id -contains "SM7523") }

Probe "filter-by-status bypass on public view" "no unapproved rows" `
    { Get-Rest "profile_public_v1?select=*&limit=200" } `
    { param($o,$s) ($s -eq 200) -and (-not ($o.registry_id -contains "PEND99")) }

Probe "evidence_public_v1 hides unapproved" "no PEND99 evidence" `
    { Get-Rest "evidence_public_v1?select=registry_id&registry_id=eq.PEND99" } `
    { param($o,$s) ($s -ne 200) -or ($o.Count -eq 0) }

Probe "credential_public_v1 hides unapproved" "no PEND99 credentials" `
    { Get-Rest "credential_public_v1?select=registry_id&registry_id=eq.PEND99" } `
    { param($o,$s) ($s -ne 200) -or ($o.Count -eq 0) }

Probe "profile_render_v1 hides unapproved" "no PEND99 render" `
    { Get-Rest "profile_render_v1?select=registry_id&registry_id=eq.PEND99" } `
    { param($o,$s) ($s -ne 200) -or ($o.Count -eq 0) }

Probe "render_payload_cache raw table" "no unapproved payloads" `
    { Get-Rest "render_payload_cache?select=profile_id" } `
    { param($o,$s) ($s -ne 200) -or ($o.Count -eq 0) }

# ── 5. Storage must not serve a document without a signed link ───────────────
Probe "storage object without signed url" "denied" `
    { Invoke-RestMethod -Uri "$base/storage/v1/object/evidence_docs/" -Headers $H -Method GET } `
    { param($o,$s) $s -ne 200 }

Probe "storage bucket listing" "denied or empty" `
    { Invoke-RestMethod -Uri "$base/storage/v1/object/list/evidence_docs" -Headers $H -Method POST -ContentType "application/json" -Body '{"prefix":"","limit":100}' } `
    { param($o,$s) ($s -ne 200) -or ($o.Count -eq 0) }

# ── report ───────────────────────────────────────────────────────────────────
$results | Format-Table -AutoSize -Wrap

$failed = @($results | Where-Object { $_.Result -eq "FAIL" })
Write-Host ""
Write-Host ("{0} probes, {1} passed, {2} failed" -f $results.Count, ($results.Count - $failed.Count), $failed.Count)
if ($failed.Count) {
    Write-Host ""
    Write-Host "FAILURES:"
    $failed | ForEach-Object { Write-Host (" - {0} (expected {1}, saw {2})" -f $_.Probe, $_.Expect, $_.Saw) }
}

# Columns exposed publicly — read this by eye, not by assertion.
Write-Host ""
Write-Host "Columns visible to anyone on profile_public_v1:"
try {
    $row = Get-Rest "profile_public_v1?select=*&limit=1"
    if ($row.Count) { $row[0].PSObject.Properties.Name | ForEach-Object { Write-Host "  $_" } }
    else { Write-Host "  (view returned no rows)" }
} catch { Write-Host "  could not read: $_" }
