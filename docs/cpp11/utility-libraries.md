# `chrono`、随机数与正则表达式

阅读前建议先了解：[容器](containers.md)与[迭代器](../prerequisites.md#迭代器与算法)；时间、随机数和正则三部分彼此独立。本篇介绍的新增能力属于 C++11；后续版本差异会另行标注。

## 学习目标与旧接口问题

C++03 的时间接口大量使用裸整数和 C 结构体，随机数常依赖全局 `rand()`，正则表达式没有进入标准库。单位、随机算法、概率分布和匹配语法往往隐藏在约定中。

C++11 引入三组独立设施：`chrono` 用类型表达时间单位和时钟，`<random>` 把伪随机引擎与概率分布分开，`<regex>` 提供标准模式匹配。读完后，你应该能为耗时测量选择时钟、构造可复现随机测试，并区分整串匹配与子串搜索。

## 时间、随机数与匹配分别学习

以下片段只对比写法；完整、可运行的程序见后文。

```text
// 传统时间数值可能没有单位；chrono 把单位纳入类型
std::chrono::milliseconds timeout(500);
// 不使用全局 rand() % 6；引擎负责序列，分布负责取值范围
std::mt19937 engine(42);
std::uniform_int_distribution<int> die(1, 6);
int result = die(engine);
```

这几项接口相互独立：计时先选合适时钟，随机数先选引擎和分布，文本匹配再选 regex_match 或 regex_search。固定种子便于复现引擎序列，但分布映射不保证跨标准库得到相同序列。安全令牌不应使用这些普通伪随机引擎；固定分隔符解析也往往不需要正则。

## 第一个完整示例

示例把 2500 毫秒显式转换为整秒，用固定种子模拟一次骰子，并验证标识符字符串。

```cpp example id="cpp11-utility-libraries" std="c++11" file="main.cpp" kind="single" compilers="all" output="valid=true, seconds=2"
#include <chrono>
#include <iostream>
#include <random>
#include <regex>
#include <string>

int main() {
    const std::chrono::milliseconds elapsed(2500);
    const std::chrono::seconds seconds =
        std::chrono::duration_cast<std::chrono::seconds>(elapsed);

    std::mt19937 engine(1234);
    std::uniform_int_distribution<int> distribution(1, 6);
    const int roll = distribution(engine);
    const bool in_range = roll >= 1 && roll <= 6;

    const std::regex identifier("[A-Za-z_][A-Za-z0-9_]*");
    const bool valid = in_range && std::regex_match(std::string("value_1"), identifier);
    std::cout << std::boolalpha << "valid=" << valid << ", seconds=" << seconds.count() << '\n';
}
```

程序输出 `valid=true, seconds=2`。`duration_cast` 丢弃不足一秒的 500 毫秒；固定种子让测试可重复，但不提供安全随机性。正则表达式便于描述局部模式，复杂语法和不可信高成本输入应考虑专用解析器。

## `chrono` 的强类型时间

`duration<Rep, Period>` 由数值表示类型和编译期单位比例组成。秒、毫秒可以参与受控转换，编译器阻止会丢精度的隐式转换。`time_point<Clock, Duration>` 表示某个时钟纪元后的持续时间；不同 Clock 的时间点不能随意混算。

稳态耗时测量应使用 `steady_clock`，因为它保证单调；`system_clock` 可与日历时间转换，但可能因校时向前或向后跳。类型系统消除了把毫秒误当秒的常见接口错误，却不能替代对时钟语义的选择。

Period 是 `std::ratio`，例如 milliseconds 为 `ratio<1,1000>` 秒。duration 的算术通过 `common_type` 选择能表达双方单位的结果，2 秒+500 毫秒得到毫秒精度。Rep 可以是整数、浮点或自定义数值类型，但转换安全规则随表示性质变化。

整数 duration 从细单位到粗单位可能丢余数，因此要求显式 `duration_cast`；粗到细能精确表示时通常可隐式转换。浮点 Rep 允许更多转换，但仍要考虑舍入与范围。

`duration::zero/min/max` 提供边界，count() 取原始 Rep。业务 API 应传 duration 类型而不是裸 count，序列化时同时固定单位和数值范围。

### 时钟接口

Clock 提供 rep/period/duration/`time_point`、`is_steady` 和静态 `now()`。`high_resolution_clock` 可能只是 `system_clock` 或 `steady_clock` 别名，不承诺既最高精度又单调；耗时测量仍检查 `is_steady`/直接用 `steady_clock`。

`system_clock` 的 epoch 未由 C++11 跨平台协议固定，`time_since_epoch().count()` 不应直接持久化为无单位通用时间戳。用 `to_time_t/from_time_t` 与 C 日历接口时也要处理精度和时区格式化。

## 随机引擎与分布

引擎是确定性状态机：给定相同种子产生相同原始序列，适合可复现实验。分布把引擎输出映射到均匀整数、正态分布等目标统计分布。将二者分离允许复用引擎并清晰表达概率模型。

固定种子适合测试，生产模拟可用 `random_device` 或外部熵播种，但 `random_device` 是否真正非确定由实现决定。不要对引擎结果直接 `% n`，这可能产生模偏差；使用 `uniform_int_distribution`。

标准引擎包括线性同余、Mersenne Twister、subtract-with-carry 等模板及别名。mt19937 状态较大、周期长、可复现，不能因为名字常见就当密码学安全。`default_random_engine` 的具体算法由实现选择，不适合跨平台固定序列。

引擎提供 `min/max/operator()`、seed、discard 和流序列化状态等接口。复制引擎会复制完整状态，随后产生相同序列；并发共享同一可变引擎会数据竞争，常用每线程引擎或外部锁。

`seed_seq` 把一组整数扩散到较大引擎状态，比只塞一个低熵整数更全面，但不会凭空创造熵。生产播种需要收集足够随机源，再交给 `seed_seq`。

### 分布状态和参数

分布对象可带内部缓存，例如 `normal_distribution` 可能缓存第二个样本；`reset()` 清除此状态。复制/序列化可复现实验时要同时保存引擎和分布状态，而非只保存种子。

`param_type` 允许临时用另一组参数调用同一分布。分布的闭区间/开区间、端点和参数前置条件各不相同，`uniform_int_distribution` 是闭区间 `[a,b]`，不能类推到 real 分布。

分布映射算法的具体输出序列未必跨标准库一致，因此测试统计性质/范围；要逐位可复现的模拟协议，应固定项目自己的映射算法和版本。

## 正则引擎模型

`std::regex` 在构造时解析模式并建立内部表示，匹配时由实现的正则引擎执行。重复构造同一模式会浪费解析成本，应在安全生命周期内复用。某些模式和引擎可能出现严重回溯成本，正则并不天然是线性时间。

`regex_match` 要求整个输入匹配，`regex_search` 只寻找子串；两者混淆是高频错误。复杂语法、有嵌套结构或需要精确错误恢复时应使用专用解析器。

`basic_regex` 可选择 ECMAScript（默认）、basic、extended、awk、grep、egrep 等 grammar flag，不同语法的转义和特性不同。复制网上其他语言正则前必须确认语法模式。

构造/assign 模式失败抛 `regex_error`，可读取 code() 区分括号、转义、范围、空间等错误类别。若模式来自用户输入，编译阶段就要捕获并限制长度/复杂度。

匹配标志可控制 `not_bol`/`not_eol`、连续匹配等行为。`match_continuous` 配合 `regex_search` 可要求从起点匹配，仍与整串 `regex_match` 的结束要求不同。

### 结果和迭代器

`match_results` 含整体匹配下标 0、捕获组、prefix/suffix；未参与的可选组有 matched=false。`sub_match` 保存迭代器区间，调用 str() 才物化字符串。

`regex_iterator` 遍历非重叠匹配，`regex_token_iterator` 可遍历指定捕获或未匹配片段；零长度匹配需要理解迭代器如何前进，避免自己写循环停在同一位置。

`regex_replace` 支持替换格式和标志，但不是上下文敏感模板系统。处理转义、输出上限和恶意模式时仍要做资源控制。

## 示例解析与工程权衡

主示例显式把 2500 毫秒转换为秒，结果截断为 2；固定种子的掷骰只检查范围而不依赖跨实现的具体映射序列；正则使用整串匹配验证标识符。

代码审查时分别确认时间单位与时钟、随机种子与安全等级、正则匹配范围与最坏性能，不要把三个便利库当作无成本黑盒。

## 三类设施的实现成本

chrono 类型大多是零开销数值包装，转换常在编译期化简比例；真正 `now()` 成本来自系统时钟调用。random 引擎成本来自状态更新，分布可能有除法/对数等算法；regex 通常最重，包含解析、自动机/回溯和分配。

不要因都在“工具库”就采用同一缓存策略：duration/`time_point` 是小值对象，随机引擎是可变状态，regex 是可复用编译模式。对象所有权、线程安全和初始化时机完全不同。

基准要在目标标准库进行，尤其 C++11 早期 regex 实现的完整性和性能差异较大。最低编译器支持语言不等于其 regex 库成熟。

## `chrono` 的转换与舍入

`duration_cast` 在目标周期更粗时会截断，不进行四舍五入。负持续时间的截断方向同样应通过类型转换规则确认。C++17 才加入标准 `floor`、`ceil`、`round` 时间工具，C++11 代码需要显式定义业务舍入策略。

```cpp example id="cpp11-chrono-units" std="c++11" file="main.cpp" kind="single" compilers="all" output="milliseconds=2500, seconds=2"
#include <chrono>
#include <iostream>

int main() {
    const std::chrono::seconds seconds(2);
    const std::chrono::milliseconds remainder(500);
    const std::chrono::milliseconds total = seconds + remainder;
    const std::chrono::seconds truncated =
        std::chrono::duration_cast<std::chrono::seconds>(total);
    std::cout << "milliseconds=" << total.count()
              << ", seconds=" << truncated.count() << '\n';
}
```

## 随机数的可复现测试

引擎序列由标准算法定义，但分布如何把引擎输出映射到结果在不同实现间不必产生相同序列。因此跨标准库测试不应断言 `uniform_int_distribution` 的某个具体首值；应检查范围、统计性质或把分布封装在项目固定算法中。

```cpp example id="cpp11-random-range" std="c++11" file="main.cpp" kind="single" compilers="all" output="all-in-range=true"
#include <iostream>
#include <random>

int main() {
    std::mt19937 engine(2024);
    std::uniform_int_distribution<int> dice(1, 6);
    bool valid = true;
    for (int index = 0; index < 100; ++index) {
        const int value = dice(engine);
        valid = valid && value >= 1 && value <= 6;
    }
    std::cout << "all-in-range=" << std::boolalpha << valid << '\n';
}
```

## 正则捕获与匹配结果寿命

`smatch` 内部子匹配通常引用原始字符串的字符区间；原字符串必须在读取匹配结果期间保持有效且不发生使引用失效的修改。频繁匹配同一模式时复用已经构造的 `regex`，避免重复解析。

cmatch 对 C 字符指针迭代器，smatch 对 string::`const_iterator`，使用错误结果类型会造成重载不匹配。输入临时字符串不能安全产生长期 `match_results` 引用，先命名并保持所有者。

正则对象的 const 匹配是否可多线程共享需结合标准库线程安全一般规则：多个线程只读同一对象通常可行，但 `match_results` 必须每次独立，不能共享可变结果。

```cpp example id="cpp11-regex-captures" std="c++11" file="main.cpp" kind="single" compilers="all" output="name=cpp, version=11"
#include <iostream>
#include <regex>
#include <string>

int main() {
    const std::string text = "cpp-11";
    const std::regex pattern("([a-z]+)-([0-9]+)");
    std::smatch matches;
    if (!std::regex_match(text, matches, pattern) || matches.size() != 3) {
        return 1;
    }
    std::cout << "name=" << matches[1].str()
              << ", version=" << matches[2].str() << '\n';
}
```

## 实用库接口速查

| 设施 | 关键语义 |
| --- | --- |
| `duration<Rep,Period>` | 数值与单位都进入类型，转换可能有精度限制 |
| `time_point<Clock,D>` | 某时钟 epoch 上的 duration，不同 Clock 不可随意混用 |
| `system_clock` | 可映射民用时间但可能跳变 |
| `steady_clock` | 单调，适合测耗时，不适合持久化 epoch |
| `duration_cast` | 显式单位转换并按 Rep 规则舍入/截断 |
| 随机引擎 | 维护确定性状态，给定种子可复现序列 |
| `random_device` | 熵质量和是否确定性由实现/平台决定 |
| 分布对象 | 把引擎位映射到目标统计分布 |
| `regex` | 表达式编译可能抛 `regex_error` |
| `regex_match` | 要求整个序列匹配 |
| `regex_search` | 查找任意匹配子序列 |
| `smatch` | 保存指向原字符串的匹配范围，原数据需存活 |

## `random_shuffle` 的准确版本边界

`std::random_shuffle` 在 C++11 仍然存在，并没有在本版本被正式弃用。它到 C++14 才弃用、C++17 被移除。替代接口 `std::shuffle` 接受显式随机引擎，能让随机来源、状态和测试复现策略更清楚。

因此 C++11 项目已经可以主动迁移到 `shuffle`，但文档必须把“推荐迁移”和“本标准已弃用”区分开。类似地，`rand()` 的质量和全局状态存在工程问题，也不等于它在 C++11 被删除。

## 运行本篇示例

源码保存在本文的完整 `cpp` 围栏中。以下命令从仓库根目录执行，提取并验证本篇全部示例：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp11/utility-libraries.md
```

## 权威资料

- [时间工具](https://eel.is/c++draft/time)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
