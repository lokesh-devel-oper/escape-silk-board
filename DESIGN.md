# The Moment

I optimized for the instant a risky route resolves: the player sees the authoritative time, money, battery, and location changes immediately, followed by Ravi's reaction. That pairing makes each decision feel consequential without letting generated prose obscure whether the move actually helped.

# The Cut

I intentionally left out accounts, a persistent database, live traffic data, and an open-ended world. A compact fictional map and in-memory sessions kept the game finishable, testable, and honest about its scope. Shared durable sessions are the clearest next infrastructure step.

# The Miss

During controlled AI tests, narration attempted to introduce unsupported facts such as resource amounts, terminal outcomes, and locations outside the resolved move. The narrative guard caught those claims and replaced the text with deterministic narration, while the rules engine preserved the correct state.
