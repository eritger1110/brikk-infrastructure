# Pin Stripe to ~=12.5.1 temporarily

## Summary
Temporarily pin Stripe dependency to version ~=12.5.1 to maintain stability while preparing for the upcoming upgrade to Stripe 13.x.

## Changes
- Pin `stripe~=12.5.1` in requirements.txt
- This is a temporary measure to ensure consistent behavior

## Rationale
- Stripe 13.x introduces breaking changes that require careful testing
- Pinning to 12.5.1 provides stability while we prepare comprehensive tests
- Follow-up PR will upgrade to Stripe 13.x with proper billing portal tests

## Testing
- No functional changes to existing code
- CI will validate dependency resolution
- All existing tests should continue to pass

## Security
- No security implications from this version pinning
- Stripe 12.5.1 is a stable, secure version

## Next Steps
- Follow-up PR will upgrade to Stripe 13.x
- Billing portal tests will be added in the upgrade PR
- Documentation will be updated accordingly
