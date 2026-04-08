-- Profile 2: Regulatory Specialist — DEMO DATA / NOT A REAL PERSON

INSERT INTO biologist_profile (
    id, registry_id, full_name, professional_title, organization,
    state, city, geographic_region, years_experience,
    primary_discipline, taxonomic_focus, bio_summary,
    visibility_status, verification_status
) VALUES (
    'a1000000-0000-0000-0000-000000000002',
    'FC2402',
    'Demo Profile B (Regulatory Specialist)',
    'Principal Environmental Scientist',
    'Meridian Compliance Group',
    'California', 'Sacramento', 'west', 18,
    'Environmental Compliance', 'multi_taxa',
    'Eighteen years of regulatory and environmental compliance experience. Lead author on over 40 CEQA/NEPA environmental documents. Extensive coordination with CDFW, USFWS, and USACE. Specializes in permit acquisition, biological assessment preparation, and mitigation planning.',
    'active', 'verified'
);

INSERT INTO credential_record (id, profile_id, credential_type, title,
    issuing_authority, year_issued, verification_status,
    verification_method, verified_by)
VALUES
('b1000000-0000-0000-0000-000000000004',
 'a1000000-0000-0000-0000-000000000002', 'degree',
 'M.S. Environmental Science', 'Oregon State University',
 2008, 'verified', 'document_review', 'Admin Team'),
('b1000000-0000-0000-0000-000000000005',
 'a1000000-0000-0000-0000-000000000002', 'degree',
 'B.S. Biology', 'University of Oregon',
 2005, 'verified', 'document_review', 'Admin Team'),
('b1000000-0000-0000-0000-000000000006',
 'a1000000-0000-0000-0000-000000000002', 'certification',
 'Certified Environmental Scientist (CES)',
 'National Registry of Environmental Professionals',
 2012, 'verified', 'issuer_verification', 'Admin Team'),
('b1000000-0000-0000-0000-000000000019',
 'a1000000-0000-0000-0000-000000000002', 'license',
 'Professional Wetland Scientist (PWS)',
 'Society of Wetland Scientists',
 2015, 'verified', 'issuer_verification', 'Admin Team');

INSERT INTO experience_evidence (profile_id, domain_category,
    activity_type, species_or_system, habitat_context,
    project_type, years_applied, role_level,
    evidence_source, is_verified)
VALUES
('a1000000-0000-0000-0000-000000000002', 'regulatory_experience',
 'CEQA/NEPA environmental document preparation', NULL, NULL,
 'Environmental review', 15, 'lead',
 'Publication record', true),
('a1000000-0000-0000-0000-000000000002', 'regulatory_experience',
 'Biological assessment authorship', NULL, NULL,
 'Permit support', 12, 'lead', 'Agency submissions', true),
('a1000000-0000-0000-0000-000000000002', 'regulatory_experience',
 'CDFW Lake and Streambed Alteration coordination', NULL,
 'Riparian / aquatic', 'Permit acquisition',
 10, 'lead', 'Permit records', true),
('a1000000-0000-0000-0000-000000000002', 'regulatory_experience',
 'Section 404 Clean Water Act permitting', NULL,
 'Wetlands', 'Compliance',
 8, 'lead', 'USACE records', true),
('a1000000-0000-0000-0000-000000000002', 'field_experience',
 'Wetland delineation', NULL, 'Wetlands / riparian',
 'Regulatory support', 6, 'contributor',
 'Delineation reports', true),
('a1000000-0000-0000-0000-000000000002', 'leadership_scope',
 'Environmental compliance team management', NULL, NULL,
 'Organizational', 10, 'oversight',
 'Employer records', true),
('a1000000-0000-0000-0000-000000000002', 'leadership_scope',
 'Client and agency coordination', NULL, NULL,
 'Multi-agency projects', 14, 'lead',
 'Project correspondence', true),
('a1000000-0000-0000-0000-000000000002', 'academic_technical',
 'Technical report authorship', NULL, NULL,
 'Environmental documentation', 15, 'lead',
 'Publication list', true);
