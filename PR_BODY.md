## Summary

This PR hardens `src/models/neural_network.py` for safer production use by adding configuration validation, fixing subclassed Keras target-network initialization, making DQN-only training paths explicit, and improving replay-buffer and training-step safety checks.

## Also included

- gradient clipping and non-finite loss protection
- state/batch/action validation
- fixed `get_model_summary()` return behavior
- focused unit tests for core validation and edge cases

## Test command

```bash
PYTHONPATH=. pytest tests/test_neural_network.py -q
```

## Note

The source file URL currently points to `main`:

`https://github.com/Dj221981/Ai-morphasis-2.0-2/blob/main/src/models/neural_network.py`

These changes were made on branch:

`copilot/fix-neural-network-production-hardening`

So GitHub will only show the updated file once you switch to that branch or open the PR diff.
