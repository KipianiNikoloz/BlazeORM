## 1. Contract Tests

- [x] 1.1 Add failing tests for explicit and context-bound save of new instances, including assigned primary keys.
- [x] 1.2 Add failing tests for loaded-instance updates, autocommit, and hooks.
- [x] 1.3 Add failing tests for persisted deletion and missing/invalid Session errors.

## 2. Implementation

- [x] 2.1 Add private model lifecycle state and assign it at Session hydration and persistence boundaries.
- [x] 2.2 Implement Model save/delete delegation and dirty autocommit parity.
- [ ] 2.3 Run focused and full tests across existing dialect compiler coverage.

## 3. Documentation and Completion

- [ ] 3.1 Update README, reference documentation, and Unreleased changelog.
- [ ] 3.2 Run quality gates and validate the OpenSpec change.
- [ ] 3.3 Synchronize specifications and archive the completed change.
