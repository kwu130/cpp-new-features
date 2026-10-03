# 多态内存资源 `pmr`

阅读前建议先了解：[容器](../cpp11/containers.md)、[所有权与生命周期](../prerequisites.md#所有权与-raii)；分配器只管理存储，容器负责元素。本篇介绍的新增能力属于 C++17；后续版本差异会另行标注。

## 先问：容器从哪里取得内存

普通 `std::vector<int>` 会在需要空间时通过自己的分配器申请内存。批处理等场景可能希望一批容器共用某种分配策略，并在批次结束时集中释放存储。

传统自定义分配器会成为容器类型的一部分，例如 `vector<int, MyAllocator<int>>`。C++17 的 `std::pmr::vector<int>` 则在创建时接收一个“内存资源”，由它决定从哪里分配；换资源时仍是同一种容器类型。

## 最小示例：先管理一个整数容器

```cpp example id="cpp17-pmr-basic" std="c++17" file="main.cpp" kind="single" compilers="all" output="10 20"
#include <iostream>
#include <memory_resource>
#include <vector>
int main() {
    std::pmr::monotonic_buffer_resource resource;
    {
        std::pmr::vector<int> values(&resource);
        values.push_back(10);
        values.push_back(20);
        std::cout << values[0] << ' ' << values[1] << '\n';
    } // 先销毁容器及其元素
} // 再销毁资源，集中归还它申请的存储
```

`values` 的使用方式仍像 vector；新增的是构造时传入 `&resource`。这里的 `monotonic_buffer_resource` 会按需向上游申请块，不单独回收每一次分配，而是在释放资源时集中归还。

先记住寿命顺序：容器使用资源，所以资源必须活得更久。资源释放的是存储，容器仍负责元素的构造和析构。不能在容器还使用内存时调用 `resource.release()`。

本例没有禁止堆分配，也不保证比普通 vector 更快。先有批量分配需求或测量依据，再选择资源；下一例才加入初始缓冲区和嵌套字符串。

## 组合练习：缓冲区与嵌套字符串

示例把固定数组作为单调资源的初始缓冲区，并让向量及其嵌套字符串使用同一个资源。这里的声明顺序保证资源比容器后析构。

```cpp example id="cpp17-pmr" std="c++17" file="main.cpp" kind="single" compilers="all" output="alpha beta"
#include <array>
#include <cstddef>
#include <iostream>
#include <memory_resource>
#include <string>
#include <vector>

int main() {
    std::array<std::byte, 1024> storage{};
    std::pmr::monotonic_buffer_resource resource(storage.data(), storage.size());
    std::pmr::vector<std::pmr::string> words(&resource);
    words.emplace_back("alpha");
    words.emplace_back("beta");
    std::cout << words[0] << ' ' << words[1] << '\n';
}
```

程序输出 `alpha beta`。若初始缓冲区不足，单调资源会向其上游资源申请额外块；容器逐项销毁时不会让单调资源单独回收每块存储。使用资源的对象不能比资源活得更久，跨资源移动也可能退化为逐元素操作。

## 分配器问题与 `memory_resource`

传统分配器类型参与容器类型，换一种策略会产生不同容器类型并传播模板参数。PMR 容器使用 `polymorphic_allocator`，内部只保存指向 `memory_resource` 的运行期接口，因此相同 `pmr::vector<T>` 可以连接不同资源。

`memory_resource` 通过虚函数执行分配、释放和相等性比较。相较编译期分配器多一次间接调用，但通常分配本身成本更高；真正收益来自批量策略、减少系统分配和改善局部性。

公开的非虚 `allocate(bytes, alignment)`、`deallocate(pointer, bytes, alignment)` 和 `is_equal(other)` 把请求转发到受保护虚函数 `do_allocate`、`do_deallocate`、`do_is_equal`。自定义资源应继承 `memory_resource` 并覆盖后三者，而不是绕开公开契约。

分配请求同时携带字节数和对齐值，释放时必须把与原请求匹配的信息传回资源。自定义资源不能只记录指针却忽略过对齐对象，也不能把来自上游 A 的指针交给上游 B。若要在释放时恢复尺寸或来源，应在资源内部维护元数据，并把元数据自身的分配递归问题纳入设计。

`memory_resource` 接口处理原始存储，不负责构造或析构对象；这层职责由 `polymorphic_allocator` 和容器完成。资源耗尽通常通过 `bad_alloc` 报告，返回空指针不是标准分配器成功协议。自定义实现还要遵守请求为零字节时的合法返回与配对释放要求。

```cpp example id="cpp17-pmr-counting-resource" std="c++17" file="main.cpp" kind="single" compilers="all" output="balanced=true"
#include <cstddef>
#include <iostream>
#include <memory_resource>
#include <vector>

class CountingResource : public std::pmr::memory_resource {
public:
    explicit CountingResource(std::pmr::memory_resource* upstream)
        : upstream_(upstream) {}

    std::size_t allocations() const noexcept { return allocations_; }
    std::size_t deallocations() const noexcept { return deallocations_; }

private:
    void* do_allocate(std::size_t bytes, std::size_t alignment) override {
        ++allocations_;
        return upstream_->allocate(bytes, alignment);
    }

    void do_deallocate(void* pointer, std::size_t bytes,
                       std::size_t alignment) override {
        ++deallocations_;
        upstream_->deallocate(pointer, bytes, alignment);
    }

    bool do_is_equal(const std::pmr::memory_resource& other) const noexcept override {
        return this == &other;
    }

    std::pmr::memory_resource* upstream_;
    std::size_t allocations_ = 0;
    std::size_t deallocations_ = 0;
};

int main() {
    CountingResource resource(std::pmr::new_delete_resource());
    {
        std::pmr::vector<int> values(&resource);
        values.reserve(8);
        values.push_back(42);
    }

    const bool balanced = resource.allocations() > 0 &&
                          resource.allocations() == resource.deallocations();
    std::cout << std::boolalpha << "balanced=" << balanced << '\n';
}
```

计数资源把真实请求转发给 `new_delete_resource`，同时记录分配/释放次数。示例不假定 `vector` 的具体增长次数，只验证确实发生过分配，并且容器析构后每次请求都配对释放。`do_is_equal` 采用对象身份语义：只有同一个资源实例才互相等价。

### 资源相等性的含义

`is_equal` 不是比较统计字段或资源类型名称，而是在问“由一个资源分配的内存，能否由另一个资源正确释放”。自定义资源若共享同一后端池，可以报告相等；仅仅采用相同配置但管理独立池的两个对象通常不能。

`operator==`/`!=` 最终依据资源身份或 `is_equal` 语义。错误地报告相等会让容器把内存交给不兼容资源释放，后果可能是内存破坏；过于保守地报告不等通常只会失去常数时间移动等优化。

## 单调缓冲区资源

`monotonic_buffer_resource` 从初始缓冲区顺序切块，单次 `deallocate` 通常不回收，销毁资源时一次释放全部上游块。分配接近指针递增，非常适合解析请求、构建 AST、帧临时数据等同生命周期对象图。

初始缓冲区耗尽后默认向上游资源申请更多块。若业务要求严格禁止堆分配，可把 `null_memory_resource()` 作为上游，并处理 `bad_alloc`。

`release()` 一次释放资源从上游取得的所有内存，并重置分配状态，但调用前必须确保没有对象仍使用这些存储。对单个容器调用 `clear()` 会析构元素，却不要求单调资源回收对应字节；这正是“批量生命周期换取快速分配”的代价。

初始缓冲区地址和大小由调用方提供，资源不拥有该数组。栈上缓冲区必须比资源以及所有分配对象活得更久。对齐请求可能在缓冲区开头产生填充，不能简单用对象数量乘尺寸估算必然容量。

上游块增长策略是实现细节。想要硬性内存上限时，使用拒绝额外分配的上游并测试最坏输入；仅提供一个固定初始缓冲区并不等于禁止后备堆分配。

## 池资源

`unsynchronized_pool_resource` 为不同大小类别维护内存池，适合单线程或由外部同步保护的多次分配/释放模式；`synchronized_pool_resource` 内部支持多线程访问，但会增加同步成本。二者都可以通过 `pool_options` 调整最大块尺寸和每块缓存数量，具体策略仍由实现决定。

池资源会把较大请求或不适合池的请求交给上游。释放小对象通常把块归还池内复用，而不是立刻归还操作系统。与单调资源相比，池支持单次回收再利用，适合生命周期交错的同类小对象；与通用分配器相比，它用资源生命周期和内存驻留换取更低重复分配成本。

非同步资源不得被多个线程无保护同时访问。即便每个线程操作不同容器，只要它们共享同一资源，内部池元数据仍是共享状态。常见方案是每线程资源，或明确选择同步池。

池按“块大小类别”而不是 C++ 类型组织复用，所以相同大小/对齐需求的不同对象可能共享池。资源只看到字节请求，不知道对象构造是否成功、类型是否含敏感数据。需要清零、保护页或安全擦除时，应在自定义资源或对象层明确实现，不能假定标准池提供。

`release()` 会把池持有的内存归还上游并使相关分配全部不可再使用。它不是对活对象逐个调用析构的垃圾收集器；调用者必须先析构所有使用该资源的对象。资源析构具有同样的批量存储终止边界。

## 传播与嵌套对象

PMR 容器构造元素时会通过 uses-allocator 机制把资源传播给支持它的嵌套 PMR 类型。示例的 `pmr::string` 因此使用同一单调资源。普通 `std::string` 不会自动改用该资源。

资源不是拥有型智能指针。容器只保存裸资源指针，资源必须比所有分配自它的对象活得更久。把局部资源构造的容器返回给调用方会产生悬空分配器。

`polymorphic_allocator<T>` 保存资源指针，并把字节请求换算成 `T` 对象存储。PMR 容器别名把这个分配器选作默认分配器类型，因此不同资源不会改变容器的 C++ 类型。

### `polymorphic_allocator` 的传播特征

多态分配器刻意把资源选择绑定到目标对象，而不是让普通复制/移动赋值随意传播源资源。容器赋值时目标通常继续使用自身资源；若资源不同，移动赋值可能退化为元素级搬迁。这个设计避免一个赋值悄然让目标对象依赖寿命更短的源资源。

`select_on_container_copy_construction` 对多态分配器的行为也需要单独理解：普通复制构造未必继承源资源，可能使用当前默认资源。需要确定资源时，应使用接收 allocator 的容器构造函数，例如显式把目标 `memory_resource*` 传入，而不是依赖进程默认值。

嵌套 uses-allocator 构造会把外层分配器转换成元素期望的形式，但前提是元素类型声明了相应协议并具有匹配构造函数。自定义 allocator-aware 类型应测试普通构造、复制到同资源、复制到异资源、移动和异常路径，避免只在单层容器中看似工作。

uses-allocator 构造只对声明支持相应分配器协议的元素传播。`pmr::vector<pmr::string>` 能形成同一资源的嵌套对象图，而 `pmr::vector<std::string>` 的字符缓冲区仍由普通字符串分配器管理。容器节点和元素内部资源要分别审计。

把资源指针传给容器构造函数不会转移资源所有权，也不会自动使用 `shared_ptr` 延长资源生命。建议让资源成为拥有整个对象图的上层上下文成员，并按“容器先析构、资源后析构”的成员声明逆序设计类布局。

## 相等性和移动成本

两个资源若不报告相等，容器跨资源移动赋值可能必须逐元素移动到目标资源，不能只交换内部指针。性能设计应把资源边界与对象生命周期边界对齐。

复制 PMR 容器时，目标使用哪个资源受 allocator-aware container 的构造/传播规则影响，不应凭普通容器直觉假定复制后仍共享源资源。需要指定目标资源时，调用明确接收 allocator 的构造形式，并用测试确认嵌套元素也传播正确。

交换使用不相等且不满足相应传播条件的分配器可能违反容器前置条件。设计“可跨请求移动”的对象时，最好让外层 API 固定资源边界，或者提供显式深拷贝到目标资源的操作。

## 默认与空资源

`get_default_resource()` 返回当前默认资源，默认初始指向 `new_delete_resource()`；`set_default_resource()` 可以替换随后默认构造的 `polymorphic_allocator` 所用资源。修改进程级默认值会影响远处代码和测试，不适合作为局部性能开关。

`new_delete_resource()` 使用全局 new/delete 语义，`null_memory_resource()` 的分配总是抛 `bad_alloc` 而释放为空操作。后者适合给预分配资源设置“不得向上游扩张”的硬边界，也适合测试耗尽路径。

默认资源指针的读写具有标准规定的同步语义，但切换默认资源仍是全局行为：已经构造的分配器继续保存原指针，之后默认构造的分配器才观察新值。测试若临时替换默认资源，必须保证恢复动作在异常路径也执行，并避免与并发创建对象的代码互相污染。

`new_delete_resource()`、`null_memory_resource()` 返回的资源对象具有适合长期引用的标准管理生命周期，但自定义资源通常没有。缓存一个裸 `memory_resource*` 时，应在类型设计中说明由谁拥有它；仅比较非空不能证明资源仍存活。

### 诊断资源与生产资源

计数、日志、泄漏检测资源常作为装饰器把请求转发上游。日志实现本身若再从同一资源分配，可能递归进入 `do_allocate`；应使用无分配记录路径、预留缓冲区或独立上游。并发统计则需要原子或外部同步，同时衡量诊断开销是否改变被测行为。

资源只能观察分配边界，看不到容器为什么请求增长。分析 PMR 效果时，应同时记录请求尺寸分布、峰值驻留、上游块数量和生命周期，而不只比较 `allocate` 调用次数。单调资源可能调用次数少，却因阶段边界过大而保留远超活对象所需的内存。

## 工程实践

先用分析工具确认分配是瓶颈，再选择资源；记录资源所有者和销毁顺序；测试缓冲区耗尽路径；不要把 PMR 当作通用“更快容器”，它优化的是特定生命周期和分配模式。

## 资源类型速查

| 设施 | 关键语义 |
| --- | --- |
| `memory_resource` | 字节分配/释放的运行期多态基类 |
| `polymorphic_allocator<T>` | 保存资源指针并适配 allocator 协议 |
| `new_delete_resource()` | 以全局 new/delete 语义作为资源 |
| `null_memory_resource()` | 分配总是抛 `bad_alloc`，用于硬上限 |
| `monotonic_buffer_resource` | 单次释放不回收，release/析构批量回收 |
| `unsynchronized_pool_resource` | 无内部线程安全的小块复用池 |
| `synchronized_pool_resource` | 支持并发访问但增加同步成本 |
| `pool_options` | 调整块类别参数，具体策略仍实现定义 |
| `is_equal` | 判断跨资源释放兼容性，不是配置文本相同 |
| 默认资源 | 只影响随后默认构造的多态分配器 |

## PMR 故障定位线索

- 容器析构崩溃：资源很可能先于容器/嵌套元素销毁。
- 仍频繁系统分配：检查初始缓冲区容量与上游请求分布。
- 内存只增不降：monotonic 单次 deallocate 本来就不回收。
- clear 后驻留不降：对象已析构但资源仍持有块等待 release。
- 跨线程崩溃：`unsynchronized_pool` 被多个线程共享。
- 内层 string 仍走堆：元素可能是 std::string 而非 pmr::string。
- 移动突然变慢：源目标资源不相等导致逐元素搬迁。
- 错误资源释放：自定义 `do_is_equal` 过度报告兼容。
- 计数资源无限递归：诊断日志/元数据又从被包装资源分配。
- 默认资源测试互相污染：全局 `set_default_resource` 未在异常路径恢复。

## 运行本篇示例

源码保存在本文的完整 `cpp` 围栏中。以下命令从仓库根目录执行，提取并验证本篇全部示例：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp17/pmr.md
```

## 权威资料

- [P0220R1：多态内存资源](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0220r1.html)
- [工作草案：Memory resources](https://eel.is/c++draft/mem.res)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
