from typing import Dict
from ray.rllib.agents.callbacks import DefaultCallbacks
from ray.rllib.env import BaseEnv
from ray.rllib.evaluation import MultiAgentEpisode, RolloutWorker
from ray.rllib.policy import Policy
import numpy as np

def equality_metric(players_rewards):
    total_reward = np.sum(players_rewards)
    if total_reward == 0: return 1
    N = len(players_rewards)
    diff_sum = 0
    for i in range(N):
        for j in  range(N):
            diff_sum += np.abs(players_rewards[i]-players_rewards[j])
    denominator =  2.0*N*total_reward 
    return 1.0 - diff_sum/denominator

class MyCallbacks(DefaultCallbacks):
    def on_episode_start(self, *, worker: RolloutWorker, base_env: BaseEnv,
                         policies: Dict[str, Policy],
                         episode: MultiAgentEpisode, env_index: int, **kwargs):
        # print("episode {} (env-idx={}) started.".format(
        #     episode.episode_id, env_index))
        self.num_of_agents = 2

        episode.user_data["extrinsic_reward"] = []
        episode.user_data["intrinsic_reward"] = []
        episode.user_data["aggress"] = []

        episode.user_data["sustain"] = []
        episode.user_data["tagged_agents"] = []
        episode.user_data["agent_rewards"] = {'agent-'+str(i):0 for i in range(self.num_of_agents)}

        episode.user_data["sustain"] = {'agent-'+str(i):[] for i in range(self.num_of_agents)}


    def on_episode_step(self, *, worker: RolloutWorker, base_env: BaseEnv,
                        episode: MultiAgentEpisode, env_index: int, **kwargs):
        
        in_reward = 0
        ex_reward = 0
        aggress = 0
        n_tagged = 0
        sustain = -1

        for i in range(self.num_of_agents ):
            agent_key = 'agent-'+str(i)
            
            info = episode.last_info_for(agent_key)
            if not info: return 
            
            ex_reward +=info.get('exR',0)
            episode.user_data["agent_rewards"][agent_key] += ex_reward
            in_reward += info.get('inR',0)
            aggress += info.get('aggress',-1)

            if(info['exR'] > 0):
                episode.user_data["sustain"][agent_key].append(info.get('iter'))


            n_tagged += info['tagged']

        episode.user_data["extrinsic_reward"].append(ex_reward)
        episode.user_data["intrinsic_reward"].append(in_reward)
        episode.user_data["tagged_agents"].append(n_tagged)
        

        if aggress >= 0: # count only the valid defections if -1 no agent did defect when other agent was in the filed
            episode.user_data["aggress"].append(aggress)
        if sustain >= 0:
            episode.user_data["sustain"].append(sustain+1) # +1 to compensate the -1 default
        
        # print(ex_reward, in_reward, n_tagged, sustain)

    def on_episode_end(self, *, worker: RolloutWorker, base_env: BaseEnv,
                       policies: Dict[str, Policy], episode: MultiAgentEpisode,
                       env_index: int, **kwargs):

        sus = 0
        for i in range(self.num_of_agents):
            agent_key = 'agent-'+str(i)
            sus += np.average(episode.user_data["sustain"][agent_key]) if len(episode.user_data["sustain"][agent_key]) >0 else 0
        sus /=self.num_of_agents

        T = len(episode.user_data["extrinsic_reward"]) # episode lenght

        episode.custom_metrics["ExReward"] = np.sum(episode.user_data["extrinsic_reward"])
        episode.custom_metrics["InReward"] = np.sum(episode.user_data["intrinsic_reward"])
        episode.custom_metrics["aggresseviness"] = np.sum(episode.user_data["aggress"])/max(1, len(episode.user_data["aggress"]))
        episode.custom_metrics["equality"] = equality_metric(list(episode.user_data["agent_rewards"].values()))
        episode.custom_metrics["Utalitarian_metric"] = episode.custom_metrics["ExReward"]/T
        episode.custom_metrics["sustainability"] = sus
        episode.custom_metrics["peace_metric"] = (T*self.num_of_agents - np.sum(episode.user_data["tagged_agents"]))/T
        
        
        

    # def on_sample_end(self, *, worker: RolloutWorker, samples: SampleBatch,
    #                   **kwargs):
    #     print("returned sample batch of size {}".format(samples.count))

    # def on_train_result(self, *, trainer, result: dict, **kwargs):
    #     print("trainer.train() result: {} -> {} episodes".format(
    #         trainer, result["episodes_this_iter"]))
    #     # you can mutate the result dict to add new fields to return
    #     result["callback_ok"] = True

    # def on_learn_on_batch(self, *, policy: Policy, train_batch: SampleBatch,
    #                       result: dict, **kwargs) -> None:
    #     result["sum_actions_in_train_batch"] = np.sum(train_batch["actions"])
    #     print("policy.learn_on_batch() result: {} -> sum actions: {}".format(
    #         policy, result["sum_actions_in_train_batch"]))

    # def on_postprocess_trajectory(
    #         self, *, worker: RolloutWorker, episode: MultiAgentEpisode,
    #         agent_id: str, policy_id: str, policies: Dict[str, Policy],
    #         postprocessed_batch: SampleBatch,
    #         original_batches: Dict[str, SampleBatch], **kwargs):
    #     print("postprocessed {} steps".format(postprocessed_batch.count))
    #     if "num_batches" not in episode.custom_metrics:
    #         episode.custom_metrics["num_batches"] = 0
    #     episode.custom_metrics["num_batches"] += 1
