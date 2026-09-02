# LLM 基础面试 QA 整理

## Q：目前主流的开源模型体系有哪些？
A：主流开源模型体系分为三类：
1. **Prefix Decoder 系**：输入双向注意力，输出单向注意力；代表模型：ChatGLM、ChatGLM2、U‑PaLM。
2. **Causal Decoder 系**：从左到右单向注意力；代表模型：LLaMA‑7B 以及各类 LLaMA 衍生模型。
3. **Encoder‑Decoder 系**：输入双向注意力，输出单向注意力；代表模型：T5、Flan‑T5、BART。

## Q：Prefix Decoder、Causal Decoder、Encoder‑Decoder 三者的区别是什么？
A：三者核心差异在于**attention mask（注意力掩码）**：
1. **Encoder‑Decoder**
- 输入采用双向注意力，对问题编码理解充分；
- 适合偏向理解类 NLP 任务；
- 缺点：长文本生成效果较差，训练效率低。
2. **Causal Decoder**
- 属于自回归语言模型，预训练与下游应用逻辑一致，token 只能看到前文内容；
- 文本生成任务效果优秀；
- 优点：训练效率高，零样本（zero‑shot）能力强，具备涌现能力。
3. **Prefix Decoder**
- 是 Causal Decoder 与 Encoder‑Decoder 的折中方案，prefix 部分 token 之间可以互相可见；
- 缺点：训练效率低。

## Q：大模型 LLM 的训练目标是什么？

A：主要包含两类训练目标：

1. **语言模型目标**：基于已有词预测下一个词，采用最大似然函数。Causal Decoder 会在全部 token 上计算损失；Prefix Decoder 仅在输出部分计算损失，因此训练效率：Prefix Decoder ＜ Causal Decoder。
2. **去噪自编码器**：随机替换部分文本片段，训练模型还原被破坏的文本；实现难度更高；代表模型：GLM‑130B、T5。

## Q：涌现能力产生的原因有哪些猜想？

A：论文与行业分析主要有两个猜想：

1. 任务评价指标本身不够平滑；
2. 复杂任务由多个子任务组合而成：子任务指标随模型规模是平滑提升，但组合后的整体任务指标会出现跳跃式增长，表现为涌现现象。例如复杂任务 T 由 5 个子任务构成，子任务效果从 40% 提升至 60%，但整体任务指标仅从 1.1% 提升到 7%，宏观上就体现出涌现。

## Q：为什么现在大部分大模型采用 Decoder‑only 结构？

A：

1. Decoder‑only 在无微调数据的前提下 zero‑shot 零样本表现最好；Encoder‑Decoder 需要大量标注数据做多任务微调才能发挥最佳性能。现代大模型基于海量无标注语料做自监督训练，Decoder‑only 可以更好利用无标注数据。
2. 具备训练效率、工程实现层面的优势。
3. 理论上 Encoder 双向注意力会带来低秩问题，削弱模型表达能力；对于生成任务，双向注意力没有实质收益。
4. Encoder‑Decoder 效果好部分原因来自参数量翻倍；同等参数量、同等推理成本下，Decoder‑only 是更优选择。

## Q：简单 介绍下大模型 LLMs？

A：大模型一般指参数规模 1 亿以上的模型，该标准还在不断升级，现在也出现了万亿参数规模的模型。大语言模型 LLM 是专门面向语言任务的大模型。

## Q：大模型后面标注的 175B、60B、540B 代表什么含义？

A：B 代表 Billion，即十亿，代表模型参数数量。例如 175B 就是 1750 亿参数，是 ChatGPT 大致的参数规模。

## Q：大语言模型 LLMs 有哪些优点？

A：

1. **预训练‑微调范式**：使用海量无标注数据训练通用底座，再用少量标注数据微调适配业务，降低标注成本，提升模型泛化能力。
2. **生成能力**：可以生成文本、图像、音乐等新颖内容，赋能创意、教育、娱乐等场景。
3. **涌现能力**：可以完成传统模型难以处理的任务，例如数学应用题、常识推理、符号操作等，体现出较强推理智能。

## Q：大语言模型 LLMs 有哪些缺点？

A：

1. **资源消耗巨大**：训练、推理需要大量算力与存储资源，带来较高经济成本与环境负担。例如训练 GPT‑3 约消耗 30 万美元，产生约 284 吨二氧化碳。
2. **数据与安全风险**：存在数据偏见、数据泄露、数据滥用问题，会造成模型输出错误、不合规，危害用户与社会。
3. **多项现实挑战**：可解释性弱、可靠性难以保障、可持续性不足；如何管控模型行为、保证输出稳定、平衡收益与风险，仍需要持续研究。


# transformers 操作篇 QA

## Q：如何利用 transformers 加载 Bert 模型？
A：首先导入 torch 以及 transformers 库中的`BertModel`、`BertTokenizer`；指定预训练模型名称，通过`from_pretrained`分别加载 tokenizer 与 BERT 模型。使用 tokenizer 对文本做编码得到`input_ids`，转为 torch 张量；在`torch.no_grad()`上下文下传入模型，即可拿到最后一层隐层输出。

示例核心代码：

```
import torch
from transformers import BertModel, BertTokenizer

model_name = 'bert-base-uncased'
tokenizer = BertTokenizer.from_pretrained(model_name)
model = BertModel.from_pretrained(model_name)

input_text = "Here is some text to encode"
input_ids = tokenizer.encode(input_text, add_special_tokens=True)
input_ids = torch.tensor([input_ids])

with torch.no_grad():
    last_hidden_states = model(input_ids)[0]
```

输出的`last_hidden_states`形状为`(batch_size, seq_len, hidden_size)`，每一个 token 对应 768 维向量。做二分类任务时，可以取`[CLS]`位置的向量接入线性层完成分类。

## Q：如何利用 transformers 输出 Bert 指定 hidden_state？
A：Bert‑base 默认有 12 层编码器。想要输出指定隐层状态，需要开启`output_hidden_states`参数。

- 方式一：修改模型目录下的`config.json`配置文件，将`output_hidden_states`设置为 true；
- 方式二：代码加载模型时传入参数开启。

开启之后模型返回结果中会包含`hidden_states`，可以从中挑选需要的层向量使用。

## Q：BERT 如何获取最后一层或每一层网络的向量输出？
A：

1. **last_hidden_state**：模型最后一层全部 token 的隐藏状态，shape 为`(batch_size, sequence_length, hidden_size)`。
2. **pooler_output**：取`[CLS]`token 经过线性层 + Tanh 激活后的输出，shape 为`(batch_size, hidden_size)`，该输出不一定能很好代表整体语义，实际业务更多使用均值池化等方式得到句子向量。
3. **hidden_states**：可选输出，需要配置`output_hidden_states=True`才会返回，是元组结构；索引 0 为 embedding 层输出，索引 1‑12 对应 12 层 transformer 编码器每层的输出，每层 shape 均为`(batch_size, sequence_length, hidden_size)`。
4. **attentions**：可选输出，配置`output_attentions=True`开启，保存每一层的注意力权重。

获取示例：

```
# 最后一层全部token向量
outputs.last_hidden_state
# pooler输出（处理后的CLS向量）
outputs.pooler_output
# 全部层，0号是embedding，1~12是12层encoder输出
hidden_states = outputs.hidden_states
embedding_output = hidden_states[0]
attention_hidden_states = hidden_states[1:]
```

# LLM 进阶面试 QA 整理

## Q：什么是生成式大模型？

A：生成式大模型（简称 LLMs）是可以创作文本、图片、音频、视频等全新内容的深度学习模型。相比普通深度学习模型主要有两点区别：

1. 模型参数量大，参数量达到 Billion（十亿）级别；
2. 可以通过条件、上下文引导生成全新内容，Prompt 工程就是基于该特性发展而来。

## Q：大模型是怎么让生成的文本丰富而不单调的呢？

A：分为训练、推理两个角度：

1. **训练角度**

- Transformer 大参数量模型，学习丰富多样的语言模式；
- P‑Tuning、LoRA 等微调技术降低微调成本，增强垂直领域生成多样性；
- 在训练中设计特定 loss，抑制模型输出单调内容。

2. **推理角度**

- 通过 temperature、Nucleus Sampling 等采样策略改变生成逻辑，提升输出多样性。

## Q：什么是 LLMs 复读机问题？

A：复读机指大模型出现重复输出的现象，分为 4 类：

1. **字符级别重复**：单个字、词循环输出；
2. **语句级别重复**：整句话反复生成；
3. **章节级别重复**：相同 Prompt 多次输出高度相似、缺少创新的内容；
4. 不同 Prompt 也输出相似内容，有效信息少、信息熵偏低。

## Q：为什么会出现 LLMs 复读机问题？

A：主要有如下原因：

1. **数据偏差**：预训练数据中部分短语、句子高频出现，模型复现该模式；
2. **训练目标限制**：自监督下预测下一个 token 的训练目标，容易让模型复刻输入文本；
3. **训练数据多样性不足**：缺少丰富语言表达样本，学不到多样表达方式；
4. **模型结构与解码参数**：注意力机制、生成解码策略会放大重复倾向；
5. **Induction Head 机制**：模型倾向从已经生成的 token 中挑选匹配词；高困惑度文本更容易复现重复；
6. **信息熵角度**：部分文本信息熵高，下一词概率分布平缓，模型倾向复用前文已出现 token。

## Q：如何缓解 LLMs 复读机问题？

A：分为训练、推理、后处理多种方案：

1. **Unlikelihood Training**：训练阶段增加 loss，抑制重复 token 生成；分为 token 级别、sentence 级别，sentence 级效果更优；适合抑制字符、语句重复，无法解决相同 Prompt 输出单调问题；
2. **引入噪声**：生成过程增加随机采样、随机变换，提升输出多样性；
3. **Repetition Penalty 重复惩罚**：推理阶段对已经出现的 token 降低 softmax 概率；Huggingface `generate`通过`repetition_penalty`开启；
4. **Contrastive Search**：训练使用对比 loss 降低 token 表征相似度；解码阶段惩罚和历史 token 相似度高的候选；`generate`中设置`penalty_alpha`启用；
5. **Beam Search 集束搜索**：对贪心搜索的改进，每步保留 top‑k 序列；不能根治重复，但部分场景优化输出；设置`num_beams`开启；
6. **Top‑K sampling**：只从概率最高 K 个 token 采样，增加随机性；缺点是容易生成不通顺文本；
7. **Nucleus Sampling（Top‑P）**：累计概率达到 P 阈值的候选集合内采样；相比 Top‑K，句子通顺度、指令遵循效果更好；
8. **Temperature 温度**：调节输出分布的平滑度；温度越低确定性越高，温度越高随机性越强；总结翻译任务适合低温，创意生成适合高温；
9. **No‑repeat‑ngram‑size**：强制禁止 n‑gram 重复出现，暴力抑制连续重复；
10. **重复率指标检测**：使用 seq‑rep‑4、uniq‑seq、rep、wrep 指标监控重复，异常时重生成；
11. **后处理过滤**：通过相似度规则过滤掉重复句子、短语；
12. **人工干预**：关键场景人工审核筛选输出内容。

## Q：如何处理大模型并发问题？**
A：可以从 API 调用层、缓存层、推理层三个维度进行优化：
1. **API 调用层**：管控客户端请求流量，配置最大并发请求阈值，限制接入侧并发压力。
2. **缓存层**：引入 Redis 缓存，缓存高频重复的问答结果，减少重复的模型推理调用。
3. **推理层**：配置大模型`max‑batch‑size`批处理参数，同时对模型做量化处理，提升单张显卡可承载的并发推理数量。

## Q：LLaMA 输入句子长度理论上可以无限长吗？

A：理论上 ROPE 位置编码的 LLaMA 可以支持无限长度，但实际存在多重限制：

1. **计算资源**：长序列带来算力、显存开销暴涨，容易 OOM，推理耗时大幅增加；
2. **训练与推理**：长序列训练容易梯度消失 / 爆炸；长上下文推理错误率上升；
3. **上下文建模**：超长上下文语义建模难度提升，难以捕捉长距离语义关联。

工程上可以通过分块处理、优化位置编码、高效推理算法提升长文本处理能力。

## Q：什么场景用 BERT，什么场景用 LLaMA、ChatGLM 类大模型，如何选型？

A：

1. **BERT**：双向编码器结构，擅长**NLU 自然语言理解任务**，如文本分类、实体识别、信息抽取；参数量小，部署成本低、速度快；不需要生成文本的理解任务优先选 BERT。
2. **LLaMA、ChatGLM 这类 Decoder‑only 大模型**：擅长**NLG 文本生成任务**；中文场景优先 ChatGLM，中英文混合可以选择中文 Alpaca 系列；缺点是显存要求高、推理速度慢。

> 
> 选型原则：理解类任务优先 BERT；生成类任务使用大模型。

## Q：各个专业领域是否需要各自的大模型来服务？

A：各专业领域一般需要领域定制大模型，原因：

1. **领域专有知识**：行业特有术语、知识，通用模型掌握不足；
2. **领域语言风格**：每个行业有专属表达、惯用语；
3. **业务需求差异**：金融关注数字统计，法律关注条款解析；
4. **领域数据稀缺**：领域数据少，在通用底座上做领域适配效果优于直接使用通用大模型。

实践中不需要从零训练，可以基于通用大模型做二次预训练、微调，降低成本。

## Q：如何让大模型处理更长的文本？

A：

1. **LongChat（位置缩放）**：将 position_id 按比例压缩，复用原有 RoPE 位置权重，再使用长文本对话语料微调；
2. **ALiBi**：不依赖位置编码，通过注意力偏置实现上下文扩展；
3. **稀疏注意力、MoE、Multi‑Query Attention**：从模型结构层面降低长序列算力开销；
4. **Linear Attention（如 RWKV）**：将 Attention 复杂度从\(O(N^2)\)降低到\(O(N)\)，原生适配超长序列。

> 
> 商业模型如 ChatGPT、Claude 长上下文实现未完全公开。

# LLM微调整理

## Q：如果想要在某个模型基础上做全参数微调，究竟需要多少显存？

A：在不开启 CPU Offload 的前提下，n‑B 模型全参微调最低需要 **16‑20 × n GB**显存。
以 7B 模型举例，需要多卡 A100；可以使用 FSDP、梯度累积、梯度检查点等技术降低显存占用。

## Q：为什么 SFT 之后感觉 LLM 变傻了？

A：SFT 本质是解锁、激发模型原有能力，而不是强行灌输大量新知识。

1. 如果希望靠 SFT 灌入海量领域知识，但是 SFT 数据集规模远小于预训练语料，就容易出现效果退化；
2. SFT 数据集质量差、分布不均衡、学习率设置过高，也会破坏模型原有能力。

## Q：SFT 指令微调数据如何构建？

A：

1. **代表性**：覆盖多个代表性任务；
2. **数据量**：单任务样本不宜过多，防止过拟合；
3. **任务占比均衡**：平衡各类任务样本数量，数据集整体规模一般几千到几万条，避免某一类数据主导整体分布。

## Q：领域模型 Continue PreTrain 二次预训练如何选取数据？

A：优先选择技术标准文档、专业书籍这类知识密度高的领域资料；领域网站资讯优先级低于书籍、标准文档。

## Q：领域数据训练之后通用能力下降，如何缓解灾难性遗忘？

A：领域训练过程混入通用数据集做混合训练；领域数据与通用数据常用比例 **1:5 ~ 1:10**；该比例需要结合领域数据集总量动态调整。

## Q：领域模型 Continue PreTrain，如何让模型预训练阶段学到更多下游知识？

A：采用 MIP（Multi‑Task Instruction PreTraining），二次预训练阶段混入 SFT 指令数据，预训练过程就接触下游任务。

## Q：做 SFT 的时候基座选 Base 还是 Chat 模型？

A：

1. 数据量小于 10k，资源有限：选择 Chat 基座微调；
2. 数据量充足（100k 级别），显卡资源充足：优先选择 Base 基座，更好拟合自有数据。

> 
> 在 Chat 模型微调，建议不要全参数训练，防止遗忘原生能力。

## Q：领域模型微调指令 & 输入格式有什么要求？

A：基于 Chat 模型做 SFT，**必须严格遵循模型原生对话模板、系统提示词格式**；不建议全参数训练，避免大量丢失模型原始能力。

## Q：领域微调的评测集如何构建？

A：建议构建两套评测集：

1. **选择题自动评测集**：自动化跑批，快速初筛模型效果；
2. **开放生成评测集**：人工评测，贴近真实业务场景，用于精调筛选。

## Q：领域模型词表扩增是否有必要？

A：词表扩增主要提升解码效率，对模型最终效果提升有限，按需使用。

## Q：如何训练自己的大模型？

A：

1. **方案一（全量）**
   - 阶段 1：领域二次预训练，可以做词表扩充，在海量领域文档上继续预训练基座；
   - 阶段 2：构建指令数据集，基于预训练结果做 SFT 指令微调。
2. **低成本方案**：两个阶段都使用 LoRA 微调；7B 模型 LoRA 微调单卡 3090 即可运行；全参微调则需要多卡 A100。

## Q：训练中文大模型有哪些经验？

A：

1. 扩充中文词表，可以提升中文理解效果；
2. **数据质量 > 数据数量**，高质量数据集对模型提升非常明显；
3. 增加中文样本占比，优化语言分布；
4. 在质量保证前提下，增大训练数据规模，可以显著提升效果。

## Q：指令微调有哪些好处？

A：

1. **对齐人类意图**：理解自然对话指令，对话效果更好；
2. **提升任务精度**：特定任务准确度显著提升；
3. **降低落地成本**：直接在预训练大模型微调，不用从零训练。

## Q：预训练和微调哪个阶段注入知识？

A：**预训练阶段注入知识**；微调（SFT）的作用是对齐任务格式，把预训练学到的知识适配下游任务。

## Q：想让模型学习行业领域知识，应该做预训练还是微调？

A：优先两者结合：篇章文档做二次预训练吸收领域知识，问答样本做 SFT 适配指令。

- 如果缺少大量篇章文档，领域数据量小，也可以只做 SFT 微调；
- 如果领域数据分布和基座预训练分布接近，不需要二次预训练。

## Q：多轮对话任务如何微调模型？

A：核心逻辑：把历史对话全部拼接进输入上下文。
缺点：对话轮次越多上下文越长，容易 OOM。
优化手段：

1. 对历史对话做摘要压缩；
2. 将历史对话转为 embedding；
3. 任务型对话可以传递用户意图、槽位信息。

## Q：微调后的模型出现能力劣化，灾难性遗忘是怎么回事？

A：灾难性遗忘：学习新领域知识之后，丢失原有通用能力。

- 在已经经过 SFT‑RLHF 的 Chat 模型上，如果微调数据集少、任务单一，一般不会出现严重遗忘；
- 遗忘大多来自训练参数不合理：学习率设置过高；

> 
> 建议微调学习率设置`lr=2e‑5`或者更小，不要高于预训练学习率。

## Q：微调大模型显存参考？

A：

表格

| 模型 | FP16 原生大小 | 8‑bit 量化 | 4‑bit 量化 |
| --- | --- | --- | --- |
| 7B | 13GB | 7.8GB | 3.9GB |
| 13B | 24GB | 14.9GB | 7.8GB |
| 33B | 60GB | - | 19.5GB |
| 65B | 120GB | - | - |

## Q：LLM 进行 SFT 的时候模型在学习什么？

A：

1. **预训练**：海量无监督数据学习通用语言知识，作为底座；
2. **SFT 监督微调**：基于高质量指令问答样本，学习遵循人类指令的能力，作为 RLHF 的起点；
3. **RLHF**：基于人类反馈强化学习，对齐人类偏好。

## Q：预训练和 SFT 操作有什么不同？

A：同样问答样本：

1. **预训练**：把问题 + 回答拼接在一起，输入输出全部参与 loss 计算；
2. **SFT**：构造特殊格式，只计算回答部分 loss，问句部分不参与 loss 回传；教会模型区分用户输入与模型输出，学会问答对话模式。

## Q：样本量规模增大训练出现 OOM 怎么办？

A：使用自定义数据集做分片处理：

1. 将数据集均分分配到各个 GPU 进程；
2. 每个 epoch 全局 shuffle；每个进程只加载分片大小的数据；
3. 支持直接加载已经向量化缓存好的数据。

## Q：SFT 训练如何做样本优化？

A：

1. 历史对话做左截断，保留最新对话；
2. 过滤无意义语气词；
3. 过滤脏数据、不合规对话样本；
4. 可以增加用户特征标签扩充样本信息。

## Q：微调大模型，batch size 设置太小会出现什么问题？

A：小 batch 梯度估计方差大，梯度更新噪声高；梯度累积多步可以缓解该问题。

## Q：微调大模型，batch size 设置太大会出现什么问题？

A：batch 增大到临界点之后收益递减；

- 训练 step 减少，但总计算量 FLOPS 上升；
- 固定训练 step 预算下，batch 过大模型效果反而下降。

## Q：微调大模型，batch size 该如何设置？

A：存在一个临界 batch size；需要结合噪声尺度`B_noise`；batch 和学习率要配套调优；batch 增大，学习率也需要对应调整。

## Q：微调大模型优化器如何选择？

A：主流使用 AdamW；Sophia 优化器使用梯度曲率归一化，也可以尝试，有望提升训练效率。

## Q：哪些因素会影响大模型训练内存占用？

A：模型参数量、batch size、序列长度、LoRA 参数量、数据集特性。

## Q：领域大模型二次预训练选什么数据集？

A：优先书籍、论文这类知识密度高的数据；其次领域网站、新闻资讯。

## Q：大模型微调数据集构建要点？

A：

1. 保证数据干净，具备业务代表性；
2. prompt 多样化，提升鲁棒性；
3. 多任务训练保证各个任务样本均衡。

## Q：什么是大模型训练 loss 突刺（loss spike）？

A：训练过程 loss 突然暴涨；大参数量模型更容易出现；
后果：需要很久才能恢复，严重情况下 loss 无法回落，模型无法收敛。

## Q：为什么大模型训练会出现 loss 突刺？

A：根源来自 Adam 优化器训练不稳定：

1. 训练后期浅层 Embedding 层梯度趋近于 0，参数长期得不到更新；深层参数持续更新；
2. 当 batch 样本分布发生变化，浅层突然出现巨大梯度；新旧参数状态不匹配，引发连锁反应；
3. batch 大小、梯度更新幅度、优化器 ε 超参共同影响突刺发生概率。

## Q：大模型训练 loss 突刺如何解决？

A：

1. 出现突刺后回退到之前 checkpoint，更换训练样本；
2. 降低学习率（治标不治本）；
3. 调整 Adam 优化器 ε 参数；
4. Embedding 层梯度缩放 EGS：对 embedding 梯度乘缩放系数，抑制浅层梯度爆炸；GLM‑130B 使用该方案。

## Q：分布式训练框架如何选择？

A：优先 DeepSpeed；少量节点差异不大；大规模数百节点场景 DeepSpeed 启动简单、性能分析友好。

## Q：LLMs 训练有哪些实用建议？

A：

1. 开启弹性容错、自动重启，应对长时间训练机器故障；
2. 定期保存 checkpoint 断点；
3. 训练前明确目标，记录参数配置，减少重复实验；
4. 评估真实 GPU 效率看 TFLOPS、吞吐率，不要只看 nvidia‑smi 利用率；
5. 不同框架资源开销差异明显；
6. 环境尽量使用 Docker，慎重升级底层 GLIBC 库；
7. 训练先用小模型（125M、2.7B）调通流程，再上大模型；
8. 硬件选型：时间紧张优先选择 NVIDIA 加速卡。


# LLM 训练经验面试 QA 整理

## Q：分布式训练框架如何选择？

A：优先使用 DeepSpeed，少用 PyTorch 原生 `torchrun`。节点数量较少时，不同框架差异不大；当规模达到数百节点，DeepSpeed 优势明显，启动便捷，便于做性能分析，是大规模训练的理想选择。

## Q：LLMs 训练有哪些实用建议？

A：

1. **开启弹性容错与自动重启**：大模型训练周期长达数周甚至数月，机器故障概率高；弹性容错支持故障后继续训练，自动重启可以在训练中断后快速恢复，节约时间成本。
2. **定期保存 checkpoint**：训练过程定时保存模型断点，训练中断时可以从最近断点恢复训练。
3. **训练前明确目标**：大模型训练成本高昂，训练前梳理清楚训练目的，完整记录训练参数、中间实验结果，减少重复实验。
4. **关注真实 GPU 使用效率**：不能只看 `nvidia‑smi` 的 GPU 利用率，该指标存在迷惑性；需要参考 TFLOPS、吞吐率等真实指标，DeepSpeed 内置相关监控能力。增加显卡不一定带来速度提升，很多时候是 GPU 真实利用率低下导致。
5. **注意训练框架差异**：同一模型使用不同训练框架，资源消耗差异显著。
6. **重视环境依赖问题**：搭建分布式环境时，管控 Python、pip、虚拟环境、setuptools 版本；条件允许优先使用 Docker 部署环境，规避依赖冲突。
7. **谨慎升级底层库**：遇到 GLIBC 等底层库升级提示，不要随意升级，容易引发系统宕机、命令异常。

## Q：大模型训练时如何选择模型大小？

A：训练流程调优优先从小规模模型上手，例如 OPT‑125M、2.7B，流程跑通、问题排查完毕之后，再切换到 OPT‑13B、30B 这类大模型。
业界大量优化工作都是针对 6B/7B/13B 级别模型；13B 经过指令微调之后效果可以达到 GPT‑4 约 90% 水平。

## Q：做大模型训练如何选择加速卡？

A：国产 AI 加速卡目前坑点较多；如果项目时间紧张，优先选用 Nvidia 的 AI 加速卡，减少踩坑。


# LangChain 面试 QA 整理

## Q：什么是 LangChain？

A：LangChain 是用于构建大模型端到端应用的开发框架。它提供一套工具、组件和接口，简化 LLM 应用开发；可以管理语言模型交互、组装多个组件，还能集成数据库、API 等外部资源。

## Q：LangChain 有哪些核心概念？

A：

1. **Component 和 Chain**

- Component：模块化最小构建单元，可以自由组合；
- Chain：把多个组件或者子 Chain 组合在一起，完成特定任务；一条 Chain 一般包含 Prompt 模板、语言模型、输出解析器。

2. **Prompt Templates and Values**
Prompt Template 用于生成 PromptValue，将用户输入、动态信息转换成模型接受的输入格式；PromptValue 可以转换成不同模型期望的输入类型。
3. **Example Selectors**
示例选择器，根据用户输入动态挑选 Few‑shot 示例放到 Prompt 中，提升 prompt 上下文针对性。
4. **Output Parsers**
输出解析器，提供格式化指令，将大模型原始输出解析为结构化格式，方便业务程序处理。
5. **Indexes and Retrievers**

- Index：组织管理文档，方便大模型读取；
- Retrievers：获取相关文档的接口，对接向量数据库、文本切分等工具。

6. **Chat Message History**
保存全部历史对话交互，维护会话上下文，提升多轮对话理解能力。
7. **Agents and Toolkits**

- Agent：决策实体，可以访问工具，根据用户输入自主决定调用哪个工具；
- Toolkits：一组工具集合，用来完成一类特定任务。

## Q：什么是 LangChain Agent？

A：Agent 是 LangChain 中负责决策的实体，能够访问工具集，依据用户输入自主选择调用工具。适合交互链路不确定的复杂场景，用来构建具备自适应能力的大模型应用。

## Q：LangChain 中模型抽象分为哪几类？

A：分为三类：

1. **LLM（大语言模型）**：输入文本字符串，输出文本字符串，是很多应用的基础；
2. **Chat Model（对话模型）**：接收消息列表作为输入，返回消息对象，更适合多轮对话，方便管理对话历史；
3. **Text Embedding Models（文本嵌入模型）**：输入文本，输出浮点向量，用于文档检索、相似度对比、聚类。

## Q：LangChain 主要支持哪些开发方向？

A：一共六大方向：

1. **LLM 和提示管理**：统一模型接口，管理、优化 Prompt；
2. **Chain 链**：提供标准接口编排调用链路，提供现成端到端业务链；
3. **数据增强生成**：对接外部数据源，实现文档问答、长文本摘要；
4. **Agents 智能体**：让模型自主决策、调用工具迭代完成任务；
5. **Memory 内存记忆**：维护链与 Agent 之间会话状态，提供多种记忆实现；
6. **评估**：利用大模型对生成结果做评估，弥补传统指标的短板。

## Q：LangChain 如何调用 LLM 生成回复？

A：

1. API 模型例如 OpenAI，直接导入对应 LLM 类传入参数即可调用；
2. 本地开源模型（ChatGLM 等），需要自行封装符合框架调用规范的类，实现`__call__`方法，再传入 prompt 获取返回结果。

## Q：LangChain 如何修改提示模板？

A：使用`PromptTemplate`，定义模板字符串与输入变量，调用`format()`填充变量，生成最终送入大模型的 prompt，以此引导模型输出符合预期的内容。

## Q：LangChain 如何链接多个组件完成下游任务？

A：使用`LLMChain`，传入 llm 实例和 prompt 模板，调用`run()`方法执行任务。
如果是自定义本地模型，不满足原生 LLMChain 的接口，需要自己实现 Chain 类，内部完成 prompt 格式化与模型调用。

## Q：LangChain 中 Embedding 和向量库的完整使用流程是什么？

A：

1. 选择 Embedding 模型，把文本转为高维向量；
2. 使用文本分割器将原始文档切分成多个文本块 chunk；
3. 将文本块向量化，存入向量数据库，例如 FAISS、Pinecone；
4. 用户 query 做 Embedding，在向量库中执行相似度搜索，召回 top‑k 相关文档。

## Q：LangChain 存在哪些常见问题？

A：

1. **Token 计数效率低**：框架自带 token 计数性能一般，可以使用 Tiktoken 库优化；
2. **文档质量问题**：版本迭代速度快，文档存在滞后、不准确、404 等情况；
3. **概念复杂，辅助函数过多**：大量包装函数，概念繁杂，上手难度高；
4. **行为不一致，内部细节隐藏**：部分组件会隐式修改输入内容，例如 ConversationRetrievalChain 会改写用户 query，容易破坏对话上下文；
5. **缺少标准互通数据类型**：数据格式不统一，和其他框架集成比较麻烦。

## Q：LangChain 有哪些替代框架？

A：

1. **LlamaIndex**：擅长把大模型对接自定义数据源，提供索引、查询、数据可视化工具；
2. **Deepset Haystack**：开源问答检索框架，基于 Hugging Face，适合搜索、问答类应用。

# 多轮对话长期记忆优化面试 QA 整理

## Q：多轮对话 / Agent 中维护长期记忆有哪些常见实现方式？

A：一共 8 种主流实现方案，各自适配不同业务场景：

1. **获取全量历史对话（ConversationBufferMemory）**
将完整全部对话历史直接送入 prompt。适合对话轮次不多的场景，例如普通客服；缺点是对话变长后 token 消耗快速上涨，容易触发上下文超限。
2. **滑动窗口获取最近部分对话（ConversationBufferWindowMemory）**
设置窗口大小 k，只保留最近 k 轮交互，丢弃更早历史。适合电商商品咨询，只需要关注近期问答；优点 token 可控，缺点会丢失窗口外的历史信息。
3. **提取历史对话实体信息（ConversationEntityMemory）**
从对话中抽取关键实体以及实体属性进行保存。适合法律咨询，记住案件、人名、条款等关键信息；不会存储完整原文，只维护实体字典。
4. **知识图谱记忆（ConversationKGMemory）**
抽取对话中的实体与实体关系，构建知识图谱。适合医疗咨询，记录病人症状、病史等关联关系；查询时把图谱关系转为文本放进上下文。
5. **阶段性摘要记忆（ConversationSummaryMemory）**
对全部历史对话不断做大模型摘要，用摘要代替原始对话文本。适合教育辅导长对话；缺点每轮都需要调用 LLM 做摘要，增加调用成本。
6. **摘要 + 滑动窗口组合（ConversationSummaryBufferMemory）**
保留最近几轮完整原始对话，更早的历史压缩成摘要。适合软件故障排查类技术支持场景；兼顾近期细节与早期历史，同时控制 token 总量。
7. **Token 滑动缓存（ConversationTokenBufferMemory）**
按照 token 数量而不是轮数做截断，保留 token 限额内最近关键对话。适合金融咨询；防止信息混淆，控制 prompt 总 token 大小。
8. **向量检索记忆（VectorStoreRetrieverMemory）**
把历史对话存入向量数据库，用户提问时，根据语义相似度检索相关历史片段，再塞进 prompt。适合海量长会话，无关历史不会占用 token；缺点召回质量依赖向量检索效果。

## Q：ConversationBufferMemory 的原理和适用场景是什么？

A：

- 原理：保存完整的全部对话历史，每次都把完整对话送入 prompt。
- 适用场景：轮次较少的普通客服对话。
- 缺点：对话轮次增加，token 消耗持续变大，容易触发上下文长度超限。

```
from langchain.memory import ConversationBufferMemory
memory = ConversationBufferMemory()
memory.save_context({"input": "你好"}, {"output": "怎么了"})
variables = memory.load_memory_variables({})
```

## Q：ConversationBufferWindowMemory 的原理和适用场景是什么？

A：

- 原理：设置窗口参数`k`，仅保留最近`k`轮对话，更早的内容直接丢弃。
- 适用场景：电商商品咨询，只关心最近几轮交互。
- 缺点：会丢失窗口之外的历史信息。

```
from langchain.memory import ConversationBufferWindowMemory
# 只保留最后1次互动
memory = ConversationBufferWindowMemory(k=1)
```

## Q：ConversationEntityMemory 的原理和适用场景是什么？

A：

- 原理：调用大模型从对话中提取关键实体以及实体描述信息，以字典形式存储实体，不保存全部原始对话。
- 适用场景：法律咨询，需要记住案件、人名、条款等关键信息。
- 输出会返回`history`原始对话以及`entities`实体字典。

## Q：ConversationKGMemory 的原理和适用场景是什么？

A：

- 原理：从对话抽取实体、实体之间的关系，构建知识图谱；使用时将图谱关系转换成文本片段加入上下文。
- 适用场景：医疗咨询，记录用户症状、病史等关联信息。

## Q：ConversationSummaryMemory 的原理和适用场景是什么？

A：

- 原理：不保存原始完整对话，持续调用 LLM 对历史对话生成摘要，使用摘要替代原始对话。
- 适用场景：教育辅导类长对话。
- 缺点：每轮需要调用大模型做摘要，会增加 LLM 调用开销。

## Q：ConversationSummaryBufferMemory 的原理和适用场景是什么？

A：

- 原理：混合方案，最近若干轮保留原始对话文本；超过 token 阈值的早期历史压缩为摘要。
- 适用场景：软件故障排查的技术支持，既要看近期报错细节，又需要保留早期问题背景。
- 优势：平衡上下文 token 开销与信息完整性。

## Q：ConversationTokenBufferMemory 的原理和适用场景是什么？

A：

- 原理：以 token 数量作为截断阈值，而不是对话轮次；保留 token 限额之内最近的对话。
- 适用场景：金融咨询，防止记忆过多造成信息混淆，严格控制 prompt token 上限。

## Q：VectorStoreRetrieverMemory 的原理和适用场景是什么？

A：

- 原理：将每一轮对话向量化存入向量库；用户提问时，通过语义相似度检索相关历史片段，把召回片段注入 prompt。
- 适用场景：超大量历史会话场景。
- 缺点：记忆效果高度依赖向量检索质量，存在召回不相关、漏召回风险。

```
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.memory import VectorStoreRetrieverMemory

vectorstore = Chroma(embedding_function=OpenAIEmbeddings())
retriever = vectorstore.as_retriever(search_kwargs=dict(k=1))
memory = VectorStoreRetrieverMemory(retriever=retriever)
```

## Q：多轮对话长期记忆各类方案各自主要缺点是什么？

A：

1. 全量 Buffer：对话变长 token 爆炸，容易超限；
2. 滑动窗口：直接丢弃窗口外历史，丢失信息；
3. Entity 实体记忆：只能记住实体，完整上下文会丢失；
4. KG 知识图谱：抽取实体关系会消耗 LLM，抽取错误会污染记忆；
5. Summary 摘要记忆：持续调用大模型做摘要，增加成本，摘要会丢失细节；
6. SummaryBuffer：同时有摘要 + 原始文本，依然存在 token 增长；
7. TokenBuffer：超出 token 的内容直接丢弃；
8. 向量检索记忆：依赖检索质量，存在漏召回、召回噪声问题。


# 基于 LangChain RAG 问答应用实战 QA 整理

## Q：RAG 实战整体业务流程是什么？

A：

1. **数据加载**：使用`TextLoader`读取本地文档；
2. **文档分割**：文本切分器把长文档切分为多个 chunk；
3. **向量化入库**：Embedding 模型将文本块转为向量，存入向量数据库 Chroma；
4. **Prompt 设计**：构造 RAG 提示词模板，要求模型依据检索到的背景知识回答；
5. **构建检索问答链**：使用`ConversationalRetrievalChain`实现带多轮记忆的 RAG 问答；
6. **业务调用**：传入用户问题，得到基于私有文档的回答。

## Q：LangChain 如何加载本地 txt 文档？

A：使用`TextLoader`加载本地文本文件，返回 Document 对象列表。

```
from langchain.document_loaders import TextLoader
loader = TextLoader("./藜.txt")
documents = loader.load()
```

`Document`对象包含`page_content`文档正文与`metadata`元数据（例如文件来源路径）。

## Q：文档分割使用 CharacterTextSplitter 如何配置？

A：设置`chunk_size`单块文本长度、`chunk_overlap`块之间重叠字符数，对文档列表做切分。

```
from langchain.text_splitter import CharacterTextSplitter
text_splitter = CharacterTextSplitter(chunk_size=128, chunk_overlap=0)
documents = text_splitter.split_documents(documents)
```

## Q：案例中 Embedding 模型与向量数据库分别选用什么？

A：

- Embedding 模型：`moka‑ai/m3e‑base`；
- 向量数据库：Chroma。

## Q：如何把切分后的文档向量化并存入 Chroma 向量库？

A：

```
from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain.vectorstores import Chroma

model_name = "moka-ai/m3e-base"
model_kwargs = {'device': 'cpu'}
encode_kwargs = {'normalize_embeddings': True}
embedding = HuggingFaceBgeEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs,
    query_instruction="为文本生成向量表示用于文本检索"
)
# 将文档写入Chroma
db = Chroma.from_documents(documents, embedding)
# 执行相似度检索
db.similarity_search("藜一般在几月播种?")
```

## Q：RAG 场景的 Prompt 模板设计要点是什么？

A：

1. 明确任务描述，告诉模型需要依据背景知识作答；
2. 预留`{context}`占位符，填入检索得到的背景知识；
3. 预留`{question}`占位符，填入用户问题；
4. 增加约束规则：严格使用背景知识，不能使用模型自身常识；检索不到信息时直接输出 “未找到相关答案”。

模板示例：

```
【任务描述】
请根据用户输入的上下文回答问题，并遵守回答要求。
【背景知识】
{context}
【回答要求】
- 你需要严格根据背景知识的内容回答,禁止根据常识和已知信息回答问题。
- 对于不知道的信息,直接回答“未找到相关答案”
{question}
```

## Q：ConversationalRetrievalChain 的作用是什么？

A：`ConversationalRetrievalChain`是支持**多轮对话的 RAG 链**，基于`RetrievalQAChain`扩展，集成记忆组件。
执行流程：

1. 根据聊天历史 + 当前用户问题，重构生成独立检索 query；
2. 使用重构后的 query 执行向量库检索，获取相关文档片段；
3. 将检索上下文、用户问题送入大模型，生成最终回答。

## Q：ConversationalRetrievalChain 基础调用代码示例？

A：

```
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_wenxin.llms import Wenxin

# 初始化大模型
llm = Wenxin(model="ernie-bot", baidu_api_key="baidu_api_key", baidu_secret_key="baidu_secret_key")
retriever = db.as_retriever()
# 对话记忆
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
# 构建问答链
qa = ConversationalRetrievalChain.from_llm(llm, retriever, memory=memory)
# 发起提问
res = qa({"question": "藜怎么防治虫害?"})
```

返回结果包含：`question`用户问题、`chat_history`完整对话、`answer`模型回答。

## Q：ConversationalRetrievalChain 高级自定义可以配置哪些组件？

A：

1. **question_generator**：问题生成链，基于历史对话 + 当前问题，压缩生成用于检索的 query；
2. **combine_docs_chain**：文档合并链，对检索返回的多条文档做处理、组装 prompt；
3. 可开启`return_source_documents=True`返回原始检索文档来源；
4. 可开启`return_generated_question=True`返回重构后的检索 query。

## Q：ConversationalRetrievalChain 高级自定义的返回字段有哪些？

A：

- `question`：用户原始输入问题；
- `chat_history`：历史对话记录；
- `answer`：大模型最终输出答案；
- `source_documents`：检索召回的原始文档块，包含 page_content 和 metadata 来源；
- `generated_question`：经过历史对话改写之后，用于向量检索的 query。

## Q：RAG 实战整个链路中容易踩哪些坑？

A：

1. chunk_size 设置不合理：块太大包含冗余信息，块太小语义被切割破坏；
2. embedding 模型和任务不匹配，召回结果相关性差；
3. prompt 没有强约束，模型会调用自身幻觉知识，脱离私有文档；
4. 多轮对话没有做 query 改写，历史上下文无法带入检索，导致多轮 RAG 效果变差；
5. 没有保留 source_documents，无法溯源答案来自哪段原始文档。

# LLM + 向量库文档对话（RAG）经验面试 QA 整理

## Q：为什么大模型需要外挂向量知识库，直接微调注入知识不行吗？

A：
直接使用微调注入外部知识思路：构造大量训练数据，对大模型做微调把外部知识写入模型权重。

- 优点：思路直接简单粗暴。
- 缺点：

1. 几十万量级训练数据很难完整把额外知识注入模型；
2. 训练成本极高，需要多卡并行，训练周期长。

向量知识库（RAG）不需要改动模型权重，推理阶段实时读取外部知识，成本更低、知识更新灵活，因此作为更优方案。

## Q：LLM + 向量库文档对话整体执行流程是什么？

A：

1. 加载本地文件，读取原始文本；
2. 执行文本分割，切成多个文本块 chunk；
3. 对文本块做 Embedding，存入向量库；
4. 用户提问，将用户 query 做 Embedding；
5. 向量库做相似度匹配，召回 Top‑K 最相似文本片段；
6. 将召回片段作为上下文 context，和用户问题一起填入 Prompt；
7. 将完整 Prompt 送入 LLM，生成最终回答。

## Q：LLM + 向量库文档对话的核心技术是什么？

A：核心是**Embedding 向量嵌入技术**。
知识库文档和用户提问都转化为向量，使用余弦相似度等算法计算向量相似度，检索出匹配的知识库片段作为上下文，和问题一起交给大模型生成答案。

## Q：RAG 场景下基础 prompt 模板如何构建？

A：模板示例：

```
已知信息:
{context}
根据上述已知信息，简洁和专业的来回答用户的问题。如果无法从中得到答案，请说 “根据已知信息无法回答该问题” 或 “没有提供足够的相关信息”，不允许在答案中添加编造成分，答案请使用中文。
问题是:{question}
```

要点：

1. 预留`{context}`存放检索到的文档片段；
2. 预留`{question}`存放用户原始问题；
3. 强约束：禁止模型编造内容，找不到信息要明确告知。

## Q：RAG 中文档切分粒度不好把控会带来什么问题？

A：

1. chunk 切分过小：语义被切割破坏，完整知识点被拆分，召回残缺信息；
2. chunk 切分过大：单块文本噪声变多，混入大量无关内容，加剧模型幻觉；
3. 简单按字符、换行切割，无法处理跨段落的完整语义，会出现只能召回部分要点，回答不全。

## Q：RAG 如何同时满足细粒度知识点、跨段落粗粒度知识的检索需求？

A：可以采用**二级索引架构**：

1. 第一级索引存储**关键信息摘要**，使用关键信息做 Embedding 参与向量相似度检索；
2. 检索命中之后，映射拿到对应的**完整原始文本**，交给 LLM 做推理生成。

> 
> 检索侧重点保障：高召回率、少无关信息、检索速度快；推理交给 LLM 做内容整合。

## Q：有哪些方式可以抽取文本的关键信息，用于二级索引？

A：

1. **篇章分析 Discourse Parsing**：分析段落主从从属关系，把关联段落合并为完整语义块；
2. **基于 BERT 的 NSP 下一句预测**：判断相邻段落语义是否衔接，相似度高于阈值则合并；
3. **句法分析 + NER 命名实体识别**：提取名词短语、实体、事件要素作为关键信息；
4. **语义角色标注 SRL**：提取 “谁对谁做了什么” 谓词论元信息；
5. **关键词提取工具**：KeyBERT、HanLP；
6. **垂直领域**：训练专用关键词生成小模型，如 ChatLaw 的 KeyLLM。

## Q：RAG 在垂直领域效果表现不佳，有什么解决思路？

A：

1. 对**Embedding 嵌入模型**，使用领域数据集做微调，提升领域文本向量表达效果；
2. 对**大语言模型 LLM**，使用领域问答数据做微调，提升领域理解与生成效果。

## Q：LangChain 内置简单切分做文档拆分效果差，有哪些改进手段？

A：

1. 使用语义分割模型替代简单字符切分；
2. 切分之后，判断中心句周边句子的相关性，只保留高相关上下文；
3. 先对每个文本块做摘要，基于摘要进行向量匹配检索。

## Q：如何尽可能召回和用户 query 相关的文档 Document？

A：

1. 控制文档 chunk 长度，chunk 不宜过大；高质量短 chunk 的 embedding 向量质量更高；
2. 使用领域数据微调 Embedding 模型，提升向量质量；
3. **混合检索**：向量检索（Faiss/Chroma） + 关键词检索（Elasticsearch ES）多路召回，融合结果。

## Q：拿到 context 上下文之后，如何提升 LLM 输出回答质量？

A：

1. 多版 prompt 模板对比调优，选择效果最优的提示词；
2. 使用领域问答语料对 LLM 做微调，适配业务输出格式。

## Q：Embedding 模型表示文本块偏差大是什么原因，怎么解决？

A：

### 原因

1. 开源 Embedding 模型本身能力有限，长文本 chunk 很难被一个向量完整表达；
2. 多语言场景，query 与知识库文本语言不一致，向量对齐困难。

### 解决方案

1. 使用更小的 chunk_size，配合更大 top‑k，小 chunk 噪声更低，多个召回片段拼凑完整信息；
2. 选用专门的多语言 Embedding 模型。

## Q：为什么同样的知识库，更换 prompt 之后 RAG 效果差异巨大？

A：Prompt 包含指令约束、输出格式要求。LLM 指令微调阶段已经学习特定输出范式，如果 prompt 指令、格式描述不同，模型的理解、输出行为会发生明显变化；如果需要固定输出格式，需要多轮调试指令。

## Q：不同开源 LLM 在 RAG 任务上生成效果差异大，如何处理？

A：

1. 优先选型适配中文、指令能力强的开源大模型；
2. 收集本业务领域的问答数据集，对基座模型做指令微调，让模型更好遵循 prompt 指令、固定输出格式。

## Q：RAG 项目经常出现召回的 context 和问题不相关，怎么处理？

A：

1. 做更细粒度的语义切分，避免大块无关文本混入；
2. 优化 Embedding 模型，领域数据微调；
3. 多路召回（向量 + 关键词）；
4. 增加 Rerank 重排序模型，过滤低相关性召回结果；
5. 高质量解析 PDF 等源文件，保证原始文档文本质量。

## Q：LangChain‑ChatGLM 这类本地知识库项目有哪些常见工程踩坑点？

A：

1. **Gradio 网页持续 Loading**：降低 gradio 版本，如`gradio==3.21.0`，规避高版本谷歌字体检查；
2. **PDF 加载失败**：系统安装依赖库`libmagic-dev`、`poppler‑utils`、`tesseract‑ocr`，补充中文 OCR 语言包；
3. **NLTK punkt、tagger 缺失**：手动解压数据包放到 nltk_data 指定路径；
4. **PaddleOCR 模块导入报错**：修改源码导入路径；
5. **Moss 模型动态模块加载报错**：修改加载代码，显式指定`module_file`、`class_name`；
6. **Moss 推理出现 inf/nan 张量报错**：关闭`do_sample=True`，但会带来推理卡顿问题。



