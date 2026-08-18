# Ranges 与 Views

Ranges 算法直接接受范围；Views 则以惰性、非拥有方式组合过滤和转换，管道语法让数据流更清晰。

```cpp example id="cpp20-ranges" std="c++20" file="main.cpp" kind="single" compilers="all" output="4 16"
#include <iostream>
#include <ranges>
#include <vector>

int main() {
    const std::vector<int> values{1, 2, 3, 4, 5};
    auto squares = values
        | std::views::filter([](int value) { return value % 2 == 0; })
        | std::views::transform([](int value) { return value * value; });

    bool first = true;
    for (const int value : squares) {
        std::cout << (first ? "" : " ") << value;
        first = false;
    }
    std::cout << '\n';
}
```

View 通常不拥有底层数据，必须保证源范围生命周期足够长。惰性求值意味着转换可能在每次迭代时重复执行；需要稳定结果或多次遍历时应考虑物化到容器。

## Range、迭代器和哨兵

Ranges 把“可以取得 begin/end”建模为 Concept。结束哨兵不必与迭代器同类型，这让以零字符、长度条件或无限序列结束的范围更自然。算法通过 Concept 明确要求输入范围、前向范围、随机访问范围等能力。

Ranges 算法通常返回带信息的结果类型或安全迭代器，并使用投影参数从元素中选取比较字段。它们仍是编译期泛型算法，不建立运行期集合层次。

`range<R>` 大致要求对 `R&` 能调用 `ranges::begin` 和 `ranges::end`，并让结果满足迭器/哨兵协议。`common_range` 额外要求 begin/end 类型相同；`sized_range` 能以常数或规定复杂度取得长度；`contiguous_range` 则把元素建模为连续内存。

哨兵只需要能与迭代器比较是否到达终点，不一定能解引用或递增。`sentinel_for<S, I>` 描述基本结束关系，`sized_sentinel_for` 还允许用相减得到距离。这种分离使无限序列配合 `take`、零终止字符范围和不同状态终点更自然。

### 迭代器 Concept 与旧 `iterator_category`

C++20 迭代器 Concept 以表达式能力和语义要求为中心，不再只依赖继承某个标签。`input_iterator` 支持单遍读取，`forward_iterator` 增加多遍保证，`bidirectional_iterator` 支持递减，`random_access_iterator` 支持常数时间跳转，`contiguous_iterator` 还保证地址连续。算法应要求它真正需要的最低层级。

为兼容旧迭代器，`iterator_traits` 中的标签仍参与推导，并新增 `iterator_concept` 入口。自定义迭代器若错误宣称随机访问却不能满足复杂度和代数语义，可能通过部分语法检查但让算法违反前置条件。实现操作、关联类型和复杂度承诺必须一致。

Ranges 使用 `iter_value_t`、`iter_reference_t`、`iter_rvalue_reference_t` 等分别描述值、解引用结果和迭代移动结果。代理迭代器的引用类型不一定是 `T&`；泛型代码应通过相应 traits 和 `indirectly_*` Concepts 推理，而非硬编码真实引用。

### 算法返回值与投影

Ranges 算法位于 `std::ranges`，很多能直接接收整个范围，也保留迭代器/哨兵重载。它们经常返回结构体，如同时包含输入结束位置和输出位置的 `in_out_result`，避免调用方丢失有用进度信息。

投影在比较器之前作用于元素。按成员排序不必编写重复 Lambda，可传成员指针；算法通过 `std::invoke` 语义应用投影。

```cpp example id="cpp20-ranges-projection" std="c++20" file="main.cpp" kind="single" compilers="all" output="Bob:10 Ada:20"
#include <algorithm>
#include <iostream>
#include <ranges>
#include <string>
#include <vector>

struct Player {
    std::string name;
    int score;
};

int main() {
    std::vector<Player> players{{"Ada", 20}, {"Bob", 10}};
    std::ranges::sort(players, std::ranges::less{}, &Player::score);

    bool first = true;
    for (const Player& player : players) {
        std::cout << (first ? "" : " ")
                  << player.name << ':' << player.score;
        first = false;
    }
    std::cout << '\n';
}
```

`&Player::score` 是投影，默认关系只比较投影后的整数。算法仍重排完整 `Player` 对象。若投影返回悬空引用、修改元素或不稳定地产生不同结果，排序所要求的关系性质会被破坏。

Ranges 算法通常不依赖 ADL 找到同名用户算法；它们以定制点对象形式暴露，减少某些重载意外。调用失败时，Concept 诊断会指出迭代器、可排序性或投影关系中不满足的部分。

### 定制点对象的查找顺序

`ranges::begin`、`end`、`size` 等是定制点对象，不是普通可随意取地址的重载函数集合。它们按规定顺序考虑数组、成员函数和受控 ADL 候选，并屏蔽与协议无关的普通查找结果。用户类型通常提供成员 `begin/end` 或同命名空间的自由函数即可参与。

定制时必须同时满足返回类型的 Concept，例如 `begin` 返回的对象要能作为迭代器，`end` 返回值要与其形成哨兵关系。仅让名字存在并不足够。对 const 与非 const 对象还应分别提供符合真实可变性的重载。

`ranges::size` 可来自数组长度、成员 `size`、ADL `size`，或在适当 sized sentinel 条件下由端点差得到；`disable_sized_range` 可阻止某个类型被误判为常数复杂度 sized range。标准的 `sized_range` 不只是“理论上能遍历计数”，还涉及获取大小的接口和复杂度契约。

## View 的典型表示

过滤 View 通常保存底层 View 和谓词，迭代器递增时跳过不满足元素；转换 View 保存底层 View 和转换函数，解引用时调用转换。组合管道构造一组很小的适配器对象，不会预先创建中间容器。

惰性带来零中间分配和早停优势，也意味着副作用函数可能被多次调用，调试时看到的元素并未缓存。某些 View 只满足单遍输入范围，重复遍历不是合法假设。

View 是满足 `range` 且可廉价移动、复制/销毁等特定要求的范围类型，重点是对元素序列的轻量表示。它不等同于“永远非拥有”：`owning_view` 可以拥有被适配的右值范围；但过滤、转换等适配器通常只组合底层 View 和函数对象，不物化元素。

`views::all` 是把输入规范化为 View 的核心适配：左值范围通常包装成 `ref_view`，已有 View 按值使用，合适的右值范围可进入拥有包装。管道 `range | adaptor(args...)` 本质上调用范围适配器闭包，闭包可以继续组合。

### 常用适配器

`filter` 保留谓词为真的元素，递增迭代器时寻找下一匹配；`transform` 在解引用时计算映射结果；`take`/`drop` 限制前缀；`reverse` 需要更强的双向与公共范围能力；`split`/`lazy_split` 按分隔模式产生子范围；`iota` 表示递增生成序列。

适配器会改变范围类别。对随机访问容器做 `filter` 后，寻找第 N 个匹配项不能保持普通 O(1) 随机访问；转换是否保持引用语义取决于函数返回类型。设计泛型接口时应约束实际需要的 range Concept，不要假设源容器类别一路保留。

过滤 View 可能缓存首次匹配位置以满足前向范围的复杂度要求，缓存细节影响复制后的行为和线程安全直觉。标准只保证接口契约，不能把 View 当作无状态纯函数对象。

### `subrange`：迭代器与哨兵的值对象

`ranges::subrange<I, S, K>` 把迭代器和哨兵包装成范围，可选择保存大小。它不拥有元素，底层存储失效后 subrange 同样悬空。适合把算法找到的半开区间作为一个值传给后续 Range API，而不是反复传两项参数。

当哨兵可常数时间相减时，subrange 可推导为 sized；否则若调用方明确提供长度，也可保存该长度。保存的长度必须与端点范围一致，后续若外部修改使端点含义变化，类型不会自动重新计算业务一致性。

`subrange` 可以在满足条件时转换回类似 pair 的结构化结果，也支持 `advance`、`next`、`prev` 调整窗口。调整只移动端点/大小元数据，不移动或复制元素。

## 所有权与 `borrowed_range`

从左值容器建立 View 通常保存引用；容器销毁或重分配会使 View/迭代器失效。Ranges 用 `borrowed_range` 描述临时范围销毁后迭代器是否仍安全，并以 `dangling` 返回类型阻止部分误用，但它不能捕获所有跨作用域悬空。

管道右侧适配器常保存谓词副本。捕获引用的 Lambda 会把生命周期问题带入整条管道，异步保存 View 时必须特别谨慎。

`borrowed_range<R>` 表示即使 `R` 对象本身被销毁，从它获得的迭代器仍不会因此悬空。`span`、`string_view` 等非拥有视图常属于这一类别，因为它们销毁并不销毁底层元素；普通临时 `vector` 不是。

Ranges 算法对临时非 borrowed range 的某些迭代器返回位置使用 `ranges::dangling`，让明显错误无法被当作迭代器解引用。但这只是返回类型防线：把左值容器做成 View、随后容器离开作用域，类型系统不会追踪时间关系。

`viewable_range` 控制对象是否适合交给视图适配器，综合考虑它是否已经是 View、是否为可安全引用的左值范围或可拥有的右值范围。C++20 初版与后续缺陷修正在部分细节上有调整，最低工具链应运行实际组合测试。

`enable_borrowed_range` 是面向自定义范围的显式定制变量模板，只应在范围对象销毁确实不影响迭代器有效性时特化。一个类型“内部保存指针”并不足以证明 borrowed：若它析构时释放所指缓冲区，迭代器仍会悬空。错误标记会移除 `dangling` 这道编译期防线。

View 与 borrowed range 是正交概念。某个 View 可能拥有底层范围，因此销毁 View 会销毁元素而不 borrowed；一个非 View 范围也可能只是指向外部稳定存储并满足 borrowed。API 文档应分别回答对象是否轻量可组合、迭代器是否越过范围对象寿命仍有效。

## 迭代器失效与 const

View 不能提升底层范围的稳定性。`vector` 重分配后，引用它的 `ref_view` 及派生过滤/转换链中的迭代状态同样失效。修改元素导致过滤谓词结果变化时，已有迭代器的后续行为还要满足相应 View 前置条件。

一个 View 对象是否能作为 `const` 范围遍历取决于其底层范围和适配器。谓词可能不是 const-callable，缓存也可能限制 const `begin()`。不要因为“View 是只读窗口”就假定 `const auto pipeline` 一定可遍历。

转换 View 可以返回可写引用，此时通过 View 修改底层元素；也可以返回纯值，解引用得到计算结果。API 应根据实际 `range_reference_t<R>` 判断，不把所有 Range 元素都写成容器式 `T&`。

## 性能与优化

模板组合让编译器有机会内联谓词和转换、融合循环。性能仍受分支预测、函数对象大小、重复计算和缓存访问影响。复杂 View 链不保证比手写循环更快，热路径应测量生成代码和真实数据。

惰性管道的优势包括避免中间分配、只处理消费者实际请求的元素，以及让 `take` 等早停。代价可能是每次递增重复谓词、每次解引用重复转换、复杂迭代器状态和更长模板诊断。

若结果将排序、随机多次访问、跨线程保存或重复聚合，物化一次可能更快也更安全。C++20 标准库没有统一的 `ranges::to` 容器转换；通常使用迭代构造或显式循环，注意某些 View 的迭代器/哨兵不同型，不能直接传给只接受同型迭代器对的旧构造函数。

函数对象存储在管道中，其尺寸和复制/移动语义成为 View 类型的一部分。捕获大型状态会放大管道对象；捕获指针/引用则引入生命周期。可以用拥有的小型共享状态或专门命名函数对象平衡成本。

## 与传统算法协作

传统 `<algorithm>` 多数接收同型迭代器对，而 Ranges 算法接受迭代器+哨兵或整个范围。把 View 交给旧算法时，先确认它是 `common_range`，必要时使用 `common_view` 适配；否则优先调用 `ranges::` 版本。

Range-for 与管道天然配合，因为语言会分别获取 begin/end。算法之外，格式化、容器构造和第三方 API 未必理解 View，应在边界明确适配而不是期望隐式转换。

## 示例解析与实践

示例先惰性过滤偶数，再在解引用时平方，最终只遍历一次源容器。设计管道时标记所有者、确认遍历类别、让转换保持纯净；当结果需要长期保存、排序、随机访问或反复使用时，及时物化到容器。

## Range/View 能力速查

| 设施 | 关键语义 |
| --- | --- |
| `range<R>` | 对 R& 可取得 begin/end 并形成迭代协议 |
| `sized_range` | 可按规定复杂度取得长度 |
| `common_range` | 迭代器和哨兵类型相同 |
| `contiguous_range` | 元素连续并满足地址关系 |
| `view` | 轻量范围表示，不等同于一定非拥有 |
| `views::all` | 把输入规范化为 ref/owning/已有 view |
| `borrowed_range` | 范围对象销毁后迭代器仍不因此悬空 |
| `ranges::dangling` | 阻止明显的临时非 borrowed 迭代器误用 |
| projection | 比较前通过 invoke 提取元素字段 |
| `subrange` | 非拥有地包装迭代器、哨兵和可选大小 |

## Ranges 专项审查问题

- 管道底层范围由谁拥有，何时销毁或重分配？
- View 是否只满足 `input_range`，却被代码重复遍历？
- filter/transform 中的函数对象是否含副作用或短寿命引用捕获？
- 算法实际需要的 iterator/range Concept 是否被准确约束？
- 返回迭代器面对临时非 borrowed range 时是否变成 dangling？
- 投影是否稳定、只读并形成严格弱序所需关系？
- 旧算法是否错误要求 common iterator/end，而当前 View 使用异型哨兵？
- 惰性转换是否因多次解引用重复昂贵计算？
- const View 是否真的能调用 begin，而非凭直觉假定？
- 结果跨线程、排序或重复访问前是否应该先物化？

## Ranges 故障定位线索

- 编译器报告 not range：先分别验证 ranges::begin 和 ranges::end。
- 报 `sentinel_for` 失败：检查 end 类型能否与 iterator 双向比较。
- sort 不可用：核对 `random_access`、sortable、投影和关系四层约束。
- 旧算法拒绝 View：检查 iterator/end 是否异型并考虑 `common_view`。
- 结果为 dangling：算法接收了临时非 borrowed range。
- 第二次遍历为空：当前管道可能只满足单遍 `input_range`。
- const 管道无法 begin：谓词 const-callable 或适配器缓存契约不满足。
- 元素修改未落到底层：transform 可能按值返回而非引用。
- 运行变慢：检查 filter 重复扫描、transform 重算和大型闭包捕获。
- 偶发悬空：从最外 View 逐层追踪到最终 owning/`ref_view` 与所有者。

## 权威资料

- [P0896R4：Ranges](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0896r4.pdf)
- [工作草案：Ranges library](https://eel.is/c++draft/ranges)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
