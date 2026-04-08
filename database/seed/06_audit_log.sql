-- Sample Audit Log Entries

INSERT INTO verification_audit_log
    (profile_id, previous_status, new_status,
     changed_by, change_reason)
VALUES
('a1000000-0000-0000-0000-000000000001',
 'submitted', 'pending_review', 'System',
 'Automatic on profile submission'),
('a1000000-0000-0000-0000-000000000001',
 'pending_review', 'under_verification', 'Admin Team',
 'Documents received, initiating review'),
('a1000000-0000-0000-0000-000000000001',
 'under_verification', 'verified', 'Admin Team',
 'All credentials confirmed via document review'),
('a1000000-0000-0000-0000-000000000002',
 'submitted', 'verified', 'Admin Team',
 'Full credential set verified'),
('a1000000-0000-0000-0000-000000000003',
 'submitted', 'verified', 'Admin Team',
 'Academic credentials and publication record confirmed'),
('a1000000-0000-0000-0000-000000000004',
 'submitted', 'verified', 'Admin Team',
 'Survey authorizations confirmed with USFWS'),
('a1000000-0000-0000-0000-000000000005',
 'submitted', 'verified', 'Admin Team',
 'Full multi-domain credential review completed');
