-- Profile 1: Field Specialist — DEMO DATA / NOT A REAL PERSON

INSERT INTO biologist_profile (
    id, registry_id, full_name, professional_title, organization,
    state, city, geographic_region, years_experience,
    primary_discipline, taxonomic_focus, bio_summary,
    visibility_status, verification_status
) VALUES (
    'a1000000-0000-0000-0000-000000000001',
    'FC2401',
    'Demo Profile A (Field Specialist)',
    'Senior Field Biologist',
    'Westland Environmental Services',
    'California', 'Riverside', 'southwest', 14,
    'Wildlife Biology', 'reptile',
    'Fourteen years of applied field experience across arid and semi-arid ecosystems in southern California. Specialized in desert tortoise protocol surveys, burrowing owl monitoring, and construction compliance. Biological monitor on over 60 infrastructure projects.',
    'active', 'verified'
);

INSERT INTO credential_record (id, profile_id, credential_type, title,
    issuing_authority, year_issued, verification_status,
    verification_method, verified_by)
VALUES
('b1000000-0000-0000-0000-000000000001',
 'a1000000-0000-0000-0000-000000000001', 'degree',
 'B.S. Wildlife Biology', 'University of California, Davis',
 2012, 'verified', 'document_review', 'Admin Team'),
('b1000000-0000-0000-0000-000000000002',
 'a1000000-0000-0000-0000-000000000001', 'training',
 'Desert Tortoise Council Approved Surveyor Training',
 'Desert Tortoise Council',
 2013, 'verified', 'document_review', 'Admin Team'),
('b1000000-0000-0000-0000-000000000003',
 'a1000000-0000-0000-0000-000000000001', 'permit',
 'USFWS 10(a)(1)(A) Recovery Permit — Desert Tortoise',
 'U.S. Fish and Wildlife Service',
 2016, 'verified', 'issuer_verification', 'Admin Team');

INSERT INTO experience_evidence (profile_id, domain_category,
    activity_type, species_or_system, habitat_context,
    project_type, years_applied, role_level,
    evidence_source, is_verified)
VALUES
('a1000000-0000-0000-0000-000000000001', 'field_experience',
 'Desert tortoise protocol surveys', 'Gopherus agassizii',
 'Mojave desert scrub', 'Pre-construction clearance',
 10, 'lead', 'Project reports on file', true),
('a1000000-0000-0000-0000-000000000001', 'field_experience',
 'Burrowing owl monitoring', 'Athene cunicularia',
 'Grassland / disturbed land', 'Construction compliance',
 8, 'lead', 'Monitoring reports', true),
('a1000000-0000-0000-0000-000000000001', 'field_experience',
 'Biological construction monitoring', NULL,
 'Mixed habitats', 'Infrastructure development',
 12, 'lead', 'Employer records', true),
('a1000000-0000-0000-0000-000000000001', 'species_depth',
 'Desert tortoise handling and translocation',
 'Gopherus agassizii', 'Mojave desert scrub', 'Mitigation',
 8, 'lead', 'Permit records', true),
('a1000000-0000-0000-0000-000000000001', 'species_depth',
 'Burrowing owl passive relocation', 'Athene cunicularia',
 'Grassland', 'Compliance',
 6, 'lead', 'Project reports', true),
('a1000000-0000-0000-0000-000000000001', 'regulatory_experience',
 'CEQA biological assessment support', NULL, NULL,
 'Environmental review',
 5, 'contributor', 'Report co-authorship', true),
('a1000000-0000-0000-0000-000000000001', 'leadership_scope',
 'Field crew supervision', NULL, NULL, 'Multiple projects',
 8, 'oversight', 'Employer confirmation', true);
