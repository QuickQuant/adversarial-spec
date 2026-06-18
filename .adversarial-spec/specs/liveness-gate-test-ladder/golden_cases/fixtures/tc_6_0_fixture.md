# Specification: User Profile Management

## US-101: Update Profile Picture
As a registered user, I want to upload a new profile picture so that my profile reflects my current appearance.

### Acceptance Criteria
- Supported file types: PNG, JPEG, WebP.
- Max file size: 5MB.
- Pictures must be cropped to a square aspect ratio.

### Verification Plan
The spec contains the primary success journey for US-101, but the TMR registry has
no active happy-path spine bound to this user story.

SpineCoverageChecker result:
- uncovered: ["US-101"]
- duplicate: []

Do not flag missing edge, error, boundary, negative, or unit tests for this case.
Only the missing happy-path spine is a TRACE finding.
