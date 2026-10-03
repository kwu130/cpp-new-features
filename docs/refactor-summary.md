# C++11–C++20 文档重构交付记录

本记录描述 C++11–C++20 重构阶段的范围和验证快照。随后新增的内容见 [C++23 入口](cpp23/README.md)，下述“不新增 C++23”仅描述此前阶段。

本次修改覆盖 53 篇特性专题、4 个版本入口、首页、贡献指南及权威资料页，并新增基础知识页。本记录列出修改范围与实际验证结果。保留原目录、专题文件名、原有 120 组示例 ID 和内嵌示例协议；新增 19 组，总计 139 组。不新增 C++23 专题、第三方依赖、独立源码目录或构建系统。

## 学习路径与讲解方式

主路线保持 C++11 → C++14 → C++17 → C++20，先通过[基础知识](prerequisites.md)补齐生命周期、所有权、RAII、迭代器与普通模板推导。全部专题都有前置知识链接和具体的 `--path` 运行命令。

- C++11：类型推导、初始化、范围循环与 Lambda → 类设计、复制/移动与资源管理 → 参数包、tuple、类型萃取及编译期计算 → 返回阅读完美转发。
- C++14：简单语法与日常改进 → 返回类型推导、编译期计算 → 整数序列等泛型工具。
- C++17：结构化绑定、条件初始化分别入门 → 类型与库工具 → `if constexpr`、折叠表达式及模板细节 → 并发与内存资源。
- C++20：局部语法与库改进，先建立 span 的视图认识 → Concepts → 模板 Lambda → Ranges → 并发 → 协程 → Modules。

移动、类型推导、智能指针、模板、类型萃取、编译期计算、控制流、Concepts、Ranges 和协程增加或前移小示例，采用“具体问题 → 旧写法 → 最小新写法 → 行为解释与场景 → 注意事项 → 深入原理”的阅读顺序。聚合专题先分别解释子特性，再进入综合示例。其余专题补足传统写法、适用场景或必要前置说明，保留有价值的原理与实现分析。合并智能指针重复说明和审查条目，贡献指南不再要求机械套用章节模板。

对比示例明确比较结果或行为差异；没有把语法简化笼统等同于性能提升或绝对安全。只展示局部语法的片段使用 `text` 围栏；完整程序继续使用验证器的 `cpp example` 元数据。

## 技术修订

- 移动：`std::move` 本身不转移资源；标准库“有效但值未指定”允许满足前置条件的操作，自定义类型遵循自身契约。最小示例不假定 vector 移动后的大小，演示可用的 `clear()`。
- 推导与引用：区分复制、引用绑定和值类别；基础页分别解释模板推导和实例化；结构化绑定小例比较副本与引用。
- 编译期计算：区分 `constexpr` 的可常量求值能力、`consteval` 的立即调用及立即上下文、`constinit` 的初始化保证；区分语言常量求值和优化器折叠。
- Concepts：先使用标准整数约束，再介绍 requires、组合与偏序；修正范围约束，防止仅有同名 begin/end 却无法遍历的类型通过。
- Ranges：区分 C++20 初版与 P2325R3、P2415R2、P2210R2 缺陷修正；说明 View 的移动与复杂度要求、右值范围拥有、split 与 lazy_split，以及底层对象和迭代器的不同失效规则。
- 协程：区分产出、等待、完成与挂起，先展示手动恢复再介绍生成器；`next()` 检查空句柄与完成状态，重复推进不会恢复已完成协程。明确 value 的前置条件、提前销毁与最终挂起异常约束。
- 版本与接口：明确 noexcept 成为函数类型一部分始于 C++17，嵌套 inline namespace 简写始于 C++20；核对 atomic_ref 的 cv 限制、并行策略的向量化安全边界，以及 Modules 的导出与可达性。

规范依据及缺陷修正链接集中列在[权威资料](official-sources.md)，各专题也保留对应来源。标准语义与编译器构建命令分开解释。

## 新增示例

全部源码保存在下列文档内，可使用对应专题的运行命令验证。每组只突出一个入门问题；原转发与手动恢复协程例复用并调整讲解位置。

| 示例 ID | 所在文档 |
| --- | --- |
| `cpp11-constexpr-basic-comparison` | [docs/cpp11/compile-time.md](cpp11/compile-time.md) |
| `cpp11-tuple-basic` | [docs/cpp11/functional-tools.md](cpp11/functional-tools.md) |
| `cpp11-type-trait-basic` | [docs/cpp11/functional-tools.md](cpp11/functional-tools.md) |
| `cpp11-lambda-capture-basic` | [docs/cpp11/lambdas.md](cpp11/lambdas.md) |
| `cpp11-copy-move-basic` | [docs/cpp11/move-semantics.md](cpp11/move-semantics.md) |
| `cpp11-unique-ptr-basic` | [docs/cpp11/smart-pointers.md](cpp11/smart-pointers.md) |
| `cpp11-auto-basic-comparison` | [docs/cpp11/type-deduction.md](cpp11/type-deduction.md) |
| `cpp14-constexpr-loop-comparison` | [docs/cpp14/compile-time.md](cpp14/compile-time.md) |
| `cpp14-generic-lambda-basic` | [docs/cpp14/lambdas.md](cpp14/lambdas.md) |
| `cpp17-structured-binding-basic` | [docs/cpp17/control-flow.md](cpp17/control-flow.md) |
| `cpp17-if-initializer-basic` | [docs/cpp17/control-flow.md](cpp17/control-flow.md) |
| `cpp17-if-constexpr-basic` | [docs/cpp17/control-flow.md](cpp17/control-flow.md) |
| `cpp17-ctad-basic-comparison` | [docs/cpp17/ctad.md](cpp17/ctad.md) |
| `cpp20-compile-time-basic` | [docs/cpp20/compile-time.md](cpp20/compile-time.md) |
| `cpp20-concept-basic-comparison` | [docs/cpp20/concepts.md](cpp20/concepts.md) |
| `cpp20-ranges-loop-comparison` | [docs/cpp20/ranges.md](cpp20/ranges.md) |
| `basics-reference-lifetime` | [docs/prerequisites.md](prerequisites.md) |
| `basics-iterator-algorithm` | [docs/prerequisites.md](prerequisites.md) |
| `basics-template-deduction` | [docs/prerequisites.md](prerequisites.md) |

## 验证结果与限制

- 全量执行 `python3 tools/verify_examples.py --compiler clang++`：**137 组通过，2 组按元数据跳过**。相比原基线 118 组通过，新增 19 组均通过。保留标准版本、警告参数、输出检查与超时约束。
- 去掉教学移动构造日志的无条件 noexcept 后，重新执行移动专题：**4 组通过，0 组跳过**。其后修改仅涉及文档文字、链接及本交付记录。
- 另外在临时目录验证 **7 个关键边界场景**：Concept 拒绝 double、立即函数拒绝运行期实参、拒绝 constinit/constexpr 混用、非模板 if constexpr 仍检查丢弃分支、范围约束拒绝不可遍历的伪范围、生成器空/完成/提前销毁，以及移动后手动任务不恢复空句柄。
- 结构检查覆盖全部 Markdown 的围栏闭合、相对链接与章节锚点；检查示例元数据、ID、标准版本、53 篇专题的前置链接与运行命令。原有 120 组 ID 全部保留。
- `git diff --check` 通过。仓库没有独立 Markdown lint 或文档构建配置，本机也没有 Markdown 渲染/lint 工具；此次格式验证使用结构检查，未声称完成页面渲染验证。

本机 `clang++` 与 `g++` 都是 Apple Clang，未找到真正的 GCC。跳过的是 `cpp17-execution-policies` 和 `cpp20-modules`；没有将同一工具链的别名计作第二编译器。此次未触发远程 CI，GCC、并行算法和 Modules 的实际结果尚未验证，应由现有 Ubuntu CI 的 GCC 矩阵分支或真实 GCC 环境执行全量命令确认。早期标准库是否实现相关 Ranges 缺陷修正也需在具体目标环境核对。

后续可在已有 CI 结果中检查 GCC 分支，并根据读者反馈继续细化例题；这些检查不改变此次已完成的文档范围。本次未提交或推送。

## 修改文件清单

共修改 60 个已有文件，新增 `docs/prerequisites.md` 与本记录，共 62 个文件。验证器与 CI 配置保持原有实现。

### 入口与公共文档

- [CONTRIBUTING.md](../CONTRIBUTING.md)
- [README.md](../README.md)
- [docs/official-sources.md](official-sources.md)
- [docs/prerequisites.md](prerequisites.md)
- [docs/refactor-summary.md](refactor-summary.md)

### C++11：14 篇专题与版本入口

- [docs/cpp11/README.md](cpp11/README.md)
- [docs/cpp11/class-improvements.md](cpp11/class-improvements.md)
- [docs/cpp11/compile-time.md](cpp11/compile-time.md)
- [docs/cpp11/concurrency.md](cpp11/concurrency.md)
- [docs/cpp11/containers.md](cpp11/containers.md)
- [docs/cpp11/core-utilities.md](cpp11/core-utilities.md)
- [docs/cpp11/functional-tools.md](cpp11/functional-tools.md)
- [docs/cpp11/initialization.md](cpp11/initialization.md)
- [docs/cpp11/lambdas.md](cpp11/lambdas.md)
- [docs/cpp11/move-semantics.md](cpp11/move-semantics.md)
- [docs/cpp11/range-for.md](cpp11/range-for.md)
- [docs/cpp11/smart-pointers.md](cpp11/smart-pointers.md)
- [docs/cpp11/templates.md](cpp11/templates.md)
- [docs/cpp11/type-deduction.md](cpp11/type-deduction.md)
- [docs/cpp11/utility-libraries.md](cpp11/utility-libraries.md)

### C++14：7 篇专题与版本入口

- [docs/cpp14/README.md](cpp14/README.md)
- [docs/cpp14/compile-time.md](cpp14/compile-time.md)
- [docs/cpp14/integer-sequence.md](cpp14/integer-sequence.md)
- [docs/cpp14/lambdas.md](cpp14/lambdas.md)
- [docs/cpp14/library-enhancements.md](cpp14/library-enhancements.md)
- [docs/cpp14/literals.md](cpp14/literals.md)
- [docs/cpp14/make-unique.md](cpp14/make-unique.md)
- [docs/cpp14/return-type-deduction.md](cpp14/return-type-deduction.md)

### C++17：15 篇专题与版本入口

- [docs/cpp17/README.md](cpp17/README.md)
- [docs/cpp17/charconv.md](cpp17/charconv.md)
- [docs/cpp17/concurrency.md](cpp17/concurrency.md)
- [docs/cpp17/containers.md](cpp17/containers.md)
- [docs/cpp17/control-flow.md](cpp17/control-flow.md)
- [docs/cpp17/copy-elision.md](cpp17/copy-elision.md)
- [docs/cpp17/ctad.md](cpp17/ctad.md)
- [docs/cpp17/filesystem.md](cpp17/filesystem.md)
- [docs/cpp17/fold-expressions.md](cpp17/fold-expressions.md)
- [docs/cpp17/inline-variables.md](cpp17/inline-variables.md)
- [docs/cpp17/invoke-apply.md](cpp17/invoke-apply.md)
- [docs/cpp17/parallel-algorithms.md](cpp17/parallel-algorithms.md)
- [docs/cpp17/pmr.md](cpp17/pmr.md)
- [docs/cpp17/string-view.md](cpp17/string-view.md)
- [docs/cpp17/templates-and-attributes.md](cpp17/templates-and-attributes.md)
- [docs/cpp17/vocabulary-types.md](cpp17/vocabulary-types.md)

### C++20：17 篇专题与版本入口

- [docs/cpp20/README.md](cpp20/README.md)
- [docs/cpp20/atomic.md](cpp20/atomic.md)
- [docs/cpp20/bit-and-numbers.md](cpp20/bit-and-numbers.md)
- [docs/cpp20/chrono.md](cpp20/chrono.md)
- [docs/cpp20/compile-time.md](cpp20/compile-time.md)
- [docs/cpp20/concepts.md](cpp20/concepts.md)
- [docs/cpp20/coroutines.md](cpp20/coroutines.md)
- [docs/cpp20/designated-initialization.md](cpp20/designated-initialization.md)
- [docs/cpp20/format.md](cpp20/format.md)
- [docs/cpp20/jthread.md](cpp20/jthread.md)
- [docs/cpp20/lambdas-and-templates.md](cpp20/lambdas-and-templates.md)
- [docs/cpp20/library-conveniences.md](cpp20/library-conveniences.md)
- [docs/cpp20/modules.md](cpp20/modules.md)
- [docs/cpp20/ranges.md](cpp20/ranges.md)
- [docs/cpp20/source-location.md](cpp20/source-location.md)
- [docs/cpp20/spaceship.md](cpp20/spaceship.md)
- [docs/cpp20/span.md](cpp20/span.md)
- [docs/cpp20/synchronization.md](cpp20/synchronization.md)
