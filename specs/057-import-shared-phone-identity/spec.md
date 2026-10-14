# Member imports with shared phones

Phone is contact information, not a unique person identifier. A phone-based match
requires compatible name evidence and must not override conflicting CPF, email
or external ID. Relatives with shared surnames and a shared phone remain distinct.

For member imports with no resolved identity, a phone already in the database
and no supplied strong identifier must produce a row-level pending/error entry,
without creating or updating a member. Preview and commit share this rule.
Known exact identifiers and legitimate name expansions retain compatibility.
Providing distinct identifying data allows a separate person to be imported.
Existing pending CSV export and error contracts are reused without migrations.

Acceptance: Aluna C's identifier-free row cannot update Aluno D; their existing
independent records remain independently updateable. Missing identifiers produce
a clear request for CPF, email or registration code. No automatic historical
data repair without verified source evidence.
