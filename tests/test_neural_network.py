import numpy as np
import pytest

from src.models.neural_network import AgentLearningModel, ExperienceReplay


def test_invalid_model_type_raises():
    with pytest.raises(ValueError, match="Unsupported model_type"):
        AgentLearningModel(
            state_size=4,
            action_size=2,
            model_type="invalid",
        )


def test_invalid_state_size_raises():
    with pytest.raises(ValueError, match="state_size must be greater than 0"):
        AgentLearningModel(
            state_size=0,
            action_size=2,
            model_type="dqn",
        )


def test_target_network_initialized_and_synced():
    model = AgentLearningModel(
        state_size=4,
        action_size=2,
        model_type="dqn",
    )

    network_weights = model.network.get_weights()
    target_weights = model.target_network.get_weights()

    assert len(network_weights) > 0
    assert len(network_weights) == len(target_weights)

    for w1, w2 in zip(network_weights, target_weights):
        np.testing.assert_allclose(w1, w2)


def test_select_action_rejects_wrong_state_shape():
    model = AgentLearningModel(
        state_size=4,
        action_size=2,
        model_type="dqn",
    )

    bad_state = np.array([1.0, 2.0], dtype=np.float32)

    with pytest.raises(ValueError, match="state must have shape"):
        model.select_action(bad_state)


def test_train_step_rejects_invalid_action_range():
    model = AgentLearningModel(
        state_size=4,
        action_size=2,
        model_type="dqn",
    )

    states = np.random.randn(3, 4).astype(np.float32)
    actions = np.array([0, 1, 2], dtype=np.int32)
    rewards = np.random.randn(3).astype(np.float32)
    next_states = np.random.randn(3, 4).astype(np.float32)
    dones = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    with pytest.raises(ValueError, match="actions must be in range"):
        model.train_step(states, actions, rewards, next_states, dones)


def test_train_step_returns_finite_float():
    model = AgentLearningModel(
        state_size=4,
        action_size=2,
        model_type="dqn",
    )

    states = np.random.randn(8, 4).astype(np.float32)
    actions = np.random.randint(0, 2, size=(8,), dtype=np.int32)
    rewards = np.random.randn(8).astype(np.float32)
    next_states = np.random.randn(8, 4).astype(np.float32)
    dones = np.random.randint(0, 2, size=(8,)).astype(np.float32)

    loss = model.train_step(states, actions, rewards, next_states, dones)

    assert isinstance(loss, float)
    assert np.isfinite(loss)


def test_decay_epsilon_never_drops_below_minimum():
    model = AgentLearningModel(
        state_size=4,
        action_size=2,
        model_type="dqn",
        epsilon=0.02,
        epsilon_decay=0.1,
        epsilon_min=0.01,
    )

    model.decay_epsilon()
    assert model.epsilon == pytest.approx(0.01)

    model.decay_epsilon()
    assert model.epsilon == pytest.approx(0.01)


def test_empty_replay_buffer_sample_raises():
    replay = ExperienceReplay(max_size=10)

    with pytest.raises(ValueError, match="Cannot sample from an empty replay buffer"):
        replay.sample(1)


def test_non_positive_batch_size_raises():
    replay = ExperienceReplay(max_size=10)

    with pytest.raises(ValueError, match="batch_size must be greater than 0"):
        replay.sample(0)


def test_can_sample_behaves_correctly():
    replay = ExperienceReplay(max_size=10)

    state = np.zeros(4, dtype=np.float32)
    next_state = np.ones(4, dtype=np.float32)

    replay.add(state, 0, 1.0, next_state, False)

    assert replay.can_sample(1) is True
    assert replay.can_sample(2) is False
    assert replay.can_sample(0) is False


def test_get_model_summary_returns_text():
    model = AgentLearningModel(
        state_size=4,
        action_size=2,
        model_type="dqn",
    )

    summary = model.get_model_summary()

    assert isinstance(summary, str)
    assert len(summary.strip()) > 0


def test_policy_mode_rejects_dqn_only_methods():
    model = AgentLearningModel(
        state_size=4,
        action_size=2,
        model_type="policy_gradient",
    )

    with pytest.raises(NotImplementedError, match="supports only model_type='dqn'"):
        model.select_action(np.zeros(4, dtype=np.float32))
