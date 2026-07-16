"""
Neural Network Model for AI-morphasis Agent Learning System

This module implements deep learning models using TensorFlow/Keras for training
adaptive agents with reinforcement learning capabilities.
"""

import io
import logging
from typing import List, Tuple

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import Model, Sequential, layers
from tensorflow.keras.losses import Huber, MeanSquaredError
from tensorflow.keras.optimizers import Adam

# Configure logging
logger = logging.getLogger(__name__)


class DQNNetwork(Model):
    """
    Deep Q-Network (DQN) for agent decision-making and learning.

    This network learns to estimate action values (Q-values) for reinforcement learning.
    Used for agent action selection and policy optimization.
    """

    def __init__(
        self,
        state_size: int,
        action_size: int,
        hidden_layers: List[int] = None,
        activation: str = "relu",
        name: str = "dqn_network",
    ):
        """
        Initialize DQN Network.

        Args:
            state_size: Dimension of state space
            action_size: Number of possible actions
            hidden_layers: List of hidden layer sizes (default: [128, 64])
            activation: Activation function for hidden layers
            name: Model name
        """
        super(DQNNetwork, self).__init__(name=name)

        if hidden_layers is None:
            hidden_layers = [128, 64]

        self.state_size = state_size
        self.action_size = action_size
        self.activation = activation

        # Build network layers
        self.dense_layers = []
        for units in hidden_layers:
            self.dense_layers.append(layers.Dense(units, activation=activation))
            self.dense_layers.append(layers.BatchNormalization())
            self.dense_layers.append(layers.Dropout(0.2))

        # Output Q-value layer
        self.output_layer = layers.Dense(action_size, activation=None)

        logger.info(
            f"DQN Network initialized: state_size={state_size}, "
            f"action_size={action_size}, hidden_layers={hidden_layers}"
        )

    def call(self, states: tf.Tensor, training: bool = False) -> tf.Tensor:
        """
        Forward pass through the network.

        Args:
            states: Input state tensor [batch_size, state_size]
            training: Whether in training mode (for dropout/batchnorm)

        Returns:
            Q-values [batch_size, action_size]
        """
        x = states
        for layer in self.dense_layers:
            if isinstance(layer, layers.Dropout):
                x = layer(x, training=training)
            elif isinstance(layer, layers.BatchNormalization):
                x = layer(x, training=training)
            else:
                x = layer(x)

        return self.output_layer(x)


class PolicyNetwork(Model):
    """
    Policy Network for Actor-Critic learning.

    Learns the agent's policy (probability distribution over actions)
    for continuous and discrete action spaces.
    """

    def __init__(
        self,
        state_size: int,
        action_size: int,
        hidden_layers: List[int] = None,
        action_space: str = "discrete",
        name: str = "policy_network",
    ):
        """
        Initialize Policy Network.

        Args:
            state_size: Dimension of state space
            action_size: Number of actions or action dimension
            hidden_layers: List of hidden layer sizes
            action_space: "discrete" or "continuous"
            name: Model name
        """
        super(PolicyNetwork, self).__init__(name=name)

        if hidden_layers is None:
            hidden_layers = [128, 64]

        self.state_size = state_size
        self.action_size = action_size
        self.action_space = action_space

        # Shared layers
        self.shared_layers = Sequential(
            [layers.Dense(units, activation="relu") for units in hidden_layers]
        )

        # Policy head (output probabilities)
        if action_space == "discrete":
            self.policy_head = layers.Dense(action_size, activation="softmax")
        else:
            # Continuous: mean and log-std
            self.mean = layers.Dense(action_size, activation="tanh")
            self.log_std = layers.Dense(action_size, activation=None)

        # Value head (for critic)
        self.value_head = layers.Dense(1, activation=None)

        logger.info(
            f"Policy Network initialized: state_size={state_size}, "
            f"action_size={action_size}, action_space={action_space}"
        )

    def call(
        self, states: tf.Tensor, training: bool = False
    ) -> Tuple[tf.Tensor, tf.Tensor]:
        """
        Forward pass returning policy and value estimates.

        Args:
            states: Input state tensor
            training: Whether in training mode

        Returns:
            Tuple of (policy_output, value_estimate)
        """
        shared = self.shared_layers(states, training=training)

        if self.action_space == "discrete":
            policy = self.policy_head(shared)
        else:
            mean = self.mean(shared)
            log_std = self.log_std(shared)
            policy = tf.concat([mean, log_std], axis=-1)

        value = self.value_head(shared)

        return policy, value


class AgentLearningModel:
    """
    Comprehensive learning model for AI-morphasis agents.

    Integrates DQN and Policy networks with training loops,
    experience replay, and learning optimization.
    """

    SUPPORTED_MODEL_TYPES = {"dqn", "policy_gradient"}
    SUPPORTED_DEVICES = {"cpu", "gpu"}

    def __init__(
        self,
        state_size: int,
        action_size: int,
        learning_rate: float = 0.001,
        gamma: float = 0.99,
        epsilon: float = 1.0,
        epsilon_decay: float = 0.995,
        epsilon_min: float = 0.01,
        model_type: str = "dqn",
        device: str = "cpu",
    ):
        """
        Initialize Agent Learning Model.

        Args:
            state_size: Dimension of state space
            action_size: Number of actions
            learning_rate: Learning rate for optimizer
            gamma: Discount factor for future rewards
            epsilon: Initial exploration rate (for epsilon-greedy)
            epsilon_decay: Decay rate for epsilon
            epsilon_min: Minimum epsilon value
            model_type: "dqn" or "policy_gradient"
            device: "cpu" or "gpu"
        """
        self._validate_init_params(
            state_size=state_size,
            action_size=action_size,
            learning_rate=learning_rate,
            gamma=gamma,
            epsilon=epsilon,
            epsilon_decay=epsilon_decay,
            epsilon_min=epsilon_min,
            model_type=model_type,
            device=device,
        )

        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.model_type = model_type
        self.device = device

        # Set device
        if device == "gpu" and tf.config.list_physical_devices("GPU"):
            self.device_name = "/GPU:0"
            logger.info("Using GPU for training")
        else:
            self.device_name = "/CPU:0"
            if device == "gpu":
                logger.warning("GPU requested but unavailable; falling back to CPU")
            else:
                logger.info("Using CPU for training")

        # Initialize networks
        if model_type == "dqn":
            self.network = DQNNetwork(state_size, action_size)
            self.target_network = DQNNetwork(state_size, action_size)

            dummy_input = tf.zeros((1, state_size), dtype=tf.float32)
            self.network(dummy_input, training=False)
            self.target_network(dummy_input, training=False)
            self.target_network.set_weights(self.network.get_weights())
        else:
            self.network = PolicyNetwork(state_size, action_size)
            dummy_input = tf.zeros((1, state_size), dtype=tf.float32)
            self.network(dummy_input, training=False)

        # Optimizer and loss
        self.optimizer = Adam(learning_rate=learning_rate, clipnorm=1.0)
        if model_type == "dqn":
            self.loss_fn = Huber()
        else:
            self.loss_fn = MeanSquaredError()

        # Metrics
        self.train_loss = keras.metrics.Mean(name="train_loss")

        logger.info(
            f"Agent Learning Model initialized: "
            f"model_type={model_type}, learning_rate={learning_rate}"
        )

    @classmethod
    def _validate_init_params(
        cls,
        state_size: int,
        action_size: int,
        learning_rate: float,
        gamma: float,
        epsilon: float,
        epsilon_decay: float,
        epsilon_min: float,
        model_type: str,
        device: str,
    ) -> None:
        if state_size <= 0:
            raise ValueError("state_size must be greater than 0")
        if action_size <= 0:
            raise ValueError("action_size must be greater than 0")
        if learning_rate <= 0:
            raise ValueError("learning_rate must be greater than 0")
        if not 0.0 <= gamma <= 1.0:
            raise ValueError("gamma must be between 0 and 1")
        if not 0.0 <= epsilon <= 1.0:
            raise ValueError("epsilon must be between 0 and 1")
        if not 0.0 <= epsilon_min <= 1.0:
            raise ValueError("epsilon_min must be between 0 and 1")
        if not 0.0 < epsilon_decay <= 1.0:
            raise ValueError("epsilon_decay must be in the range (0, 1]")
        if epsilon_min > epsilon:
            raise ValueError("epsilon_min cannot be greater than epsilon")
        if model_type not in cls.SUPPORTED_MODEL_TYPES:
            raise ValueError(
                f"Unsupported model_type '{model_type}'. "
                f"Expected one of {sorted(cls.SUPPORTED_MODEL_TYPES)}."
            )
        if device not in cls.SUPPORTED_DEVICES:
            raise ValueError(
                f"Unsupported device '{device}'. "
                f"Expected one of {sorted(cls.SUPPORTED_DEVICES)}."
            )

    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """
        Select action using epsilon-greedy strategy (for DQN).

        Args:
            state: Current state
            training: Whether in training mode

        Returns:
            Selected action index
        """
        if self.model_type != "dqn":
            raise NotImplementedError(
                "select_action currently supports only model_type='dqn'."
            )

        state_array = np.asarray(state, dtype=np.float32)
        if state_array.shape != (self.state_size,):
            raise ValueError(
                f"state must have shape ({self.state_size},), got {state_array.shape}"
            )

        if training and np.random.random() < self.epsilon:
            return int(np.random.randint(0, self.action_size))

        state_tensor = tf.convert_to_tensor([state_array], dtype=tf.float32)
        q_values = self.network(state_tensor, training=False)
        return int(np.argmax(q_values.numpy()[0]))

    def train_step(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        next_states: np.ndarray,
        dones: np.ndarray,
    ) -> float:
        """
        Perform one training step on a batch of experiences.

        Args:
            states: State batch [batch_size, state_size]
            actions: Action batch [batch_size]
            rewards: Reward batch [batch_size]
            next_states: Next state batch [batch_size, state_size]
            dones: Done flags [batch_size]

        Returns:
            Loss value
        """
        if self.model_type != "dqn":
            raise NotImplementedError(
                "train_step currently supports only model_type='dqn'."
            )

        states = np.asarray(states, dtype=np.float32)
        actions = np.asarray(actions, dtype=np.int32)
        rewards = np.asarray(rewards, dtype=np.float32)
        next_states = np.asarray(next_states, dtype=np.float32)
        dones = np.asarray(dones, dtype=np.float32)

        if states.ndim != 2 or states.shape[1] != self.state_size:
            raise ValueError(
                f"states must have shape [batch_size, {self.state_size}], got {states.shape}"
            )
        if next_states.ndim != 2 or next_states.shape[1] != self.state_size:
            raise ValueError(
                f"next_states must have shape [batch_size, {self.state_size}], got {next_states.shape}"
            )

        batch_size = states.shape[0]
        if batch_size == 0:
            raise ValueError("Batch must contain at least one sample")
        if actions.shape != (batch_size,):
            raise ValueError(
                f"actions must have shape ({batch_size},), got {actions.shape}"
            )
        if rewards.shape != (batch_size,):
            raise ValueError(
                f"rewards must have shape ({batch_size},), got {rewards.shape}"
            )
        if dones.shape != (batch_size,):
            raise ValueError(
                f"dones must have shape ({batch_size},), got {dones.shape}"
            )
        if np.any(actions < 0) or np.any(actions >= self.action_size):
            raise ValueError(
                f"actions must be in range [0, {self.action_size - 1}]"
            )

        with tf.device(self.device_name):
            states = tf.convert_to_tensor(states, dtype=tf.float32)
            actions = tf.convert_to_tensor(actions, dtype=tf.int32)
            rewards = tf.convert_to_tensor(rewards, dtype=tf.float32)
            next_states = tf.convert_to_tensor(next_states, dtype=tf.float32)
            dones = tf.convert_to_tensor(dones, dtype=tf.float32)

            with tf.GradientTape() as tape:
                # Predict Q-values
                q_values = self.network(states, training=True)

                # Get current Q-values for actions taken
                batch_indices = tf.range(tf.shape(q_values)[0])
                action_indices = tf.stack([batch_indices, actions], axis=1)
                current_q = tf.gather_nd(q_values, action_indices)

                # Compute target Q-values
                next_q_values = self.target_network(next_states, training=False)
                max_next_q = tf.reduce_max(next_q_values, axis=1)
                target_q = rewards + self.gamma * max_next_q * (1.0 - dones)

                # Compute loss
                loss = self.loss_fn(target_q, current_q)

            if not tf.math.is_finite(loss):
                raise ValueError("Non-finite loss encountered during training")

            gradients = tape.gradient(loss, self.network.trainable_weights)
            gradients_and_vars = [
                (grad, var)
                for grad, var in zip(gradients, self.network.trainable_weights)
                if grad is not None
            ]
            if not gradients_and_vars:
                raise ValueError("No gradients were produced during training")

            self.optimizer.apply_gradients(gradients_and_vars)

            self.train_loss.update_state(loss)
            return float(loss.numpy())

    def update_target_network(self) -> None:
        """Update target network weights from main network."""
        if self.model_type == "dqn":
            self.target_network.set_weights(self.network.get_weights())

    def decay_epsilon(self) -> None:
        """Decay epsilon for exploration."""
        if self.epsilon > self.epsilon_min:
            self.epsilon = max(
                self.epsilon_min, self.epsilon * self.epsilon_decay
            )

    def get_model_summary(self) -> str:
        """
        Get model architecture summary.

        Returns:
            Model summary string
        """
        buffer = io.StringIO()
        self.network.summary(print_fn=lambda line: buffer.write(line + "\n"))
        return buffer.getvalue()

    def save_model(self, filepath: str) -> None:
        """
        Save model weights to file.

        Args:
            filepath: Path to save model
        """
        self.network.save_weights(filepath)
        logger.info(f"Model saved to {filepath}")

    def load_model(self, filepath: str) -> None:
        """
        Load model weights from file.

        Args:
            filepath: Path to load model from
        """
        self.network.load_weights(filepath)
        if self.model_type == "dqn":
            self.target_network.set_weights(self.network.get_weights())
        logger.info(f"Model loaded from {filepath}")


class ExperienceReplay:
    """Experience replay buffer for storing and sampling agent experiences."""

    def __init__(self, max_size: int = 100000):
        """
        Initialize experience replay buffer.

        Args:
            max_size: Maximum buffer size
        """
        if max_size <= 0:
            raise ValueError("max_size must be greater than 0")

        self.max_size = max_size
        self.buffer = []
        self.position = 0

    def add(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        """
        Add experience to buffer.

        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            done: Whether episode is done
        """
        experience = (state, action, reward, next_state, done)

        if len(self.buffer) < self.max_size:
            self.buffer.append(experience)
        else:
            self.buffer[self.position] = experience

        self.position = (self.position + 1) % self.max_size

    def can_sample(self, batch_size: int) -> bool:
        """Return whether a batch of the requested size can be sampled."""
        return batch_size > 0 and len(self.buffer) >= batch_size

    def sample(
        self, batch_size: int
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Sample a batch of experiences.

        Args:
            batch_size: Size of batch to sample

        Returns:
            Tuple of (states, actions, rewards, next_states, dones)
        """
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than 0")
        if len(self.buffer) == 0:
            raise ValueError("Cannot sample from an empty replay buffer")

        if batch_size > len(self.buffer):
            batch_size = len(self.buffer)

        indices = np.random.choice(len(self.buffer), batch_size, replace=False)
        experiences = [self.buffer[i] for i in indices]

        states = np.array([e[0] for e in experiences], dtype=np.float32)
        actions = np.array([e[1] for e in experiences], dtype=np.int32)
        rewards = np.array([e[2] for e in experiences], dtype=np.float32)
        next_states = np.array([e[3] for e in experiences], dtype=np.float32)
        dones = np.array([e[4] for e in experiences], dtype=np.float32)

        return states, actions, rewards, next_states, dones

    def __len__(self) -> int:
        """Get buffer size."""
        return len(self.buffer)


if __name__ == "__main__":
    # Example usage
    logger.info("Creating example agent learning model...")

    # Create model
    model = AgentLearningModel(
        state_size=64,
        action_size=10,
        learning_rate=0.001,
        model_type="dqn",
        device="cpu",
    )

    # Create experience replay
    replay = ExperienceReplay(max_size=10000)

    # Simulate some experience
    for _ in range(100):
        state = np.random.randn(64).astype(np.float32)
        action = model.select_action(state)
        reward = float(np.random.randn())
        next_state = np.random.randn(64).astype(np.float32)
        done = bool(np.random.random() > 0.9)

        replay.add(state, action, reward, next_state, done)

    # Train on batch
    if replay.can_sample(32):
        states, actions, rewards, next_states, dones = replay.sample(32)
        loss = model.train_step(states, actions, rewards, next_states, dones)
        logger.info(f"Training loss: {loss}")

    logger.info("Example training completed successfully!")
