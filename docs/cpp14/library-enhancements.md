# `shared_timed_mutex` 与 `exchange`

## 学习目标与本篇范围

C++14 的库增强不像泛型 Lambda 那样集中在一个语法点。本篇围绕高频设施组织：共享定时互斥量与 `shared_lock`、状态替换工具 `exchange`、透明比较器带来的异构查找，以及若干小型 I/O/类型工具。

读完后，你应该能够：

- 区分共享读锁和独占写锁；
- 判断读写锁是否真的优于普通 `mutex`；
- 用 `std::exchange` 表达“写入新值并取得旧值”；
- 使用透明比较器避免查询时构造临时键；
- 避免把普通 `exchange` 误当作原子同步操作。

## 两个核心设施的最小语法

```text
std::shared_timed_mutex mutex;
std::shared_lock<std::shared_timed_mutex> read_lock(mutex);

State previous = std::exchange(current, replacement);
```

共享互斥量负责跨线程同步；`std::exchange` 只是普通对象操作，除非外部已有锁或对象本身只由一个线程访问，否则不能保证线程安全。

## 第一个完整示例

程序先持独占锁把状态从 1 替换成 2，并取得旧值，再持共享锁读取当前状态。

```cpp example id="cpp14-library-enhancements" std="c++14" file="main.cpp" kind="single" compilers="all" output="old=1, current=2"
#include <iostream>
#include <mutex>
#include <shared_mutex>
#include <utility>

int main() {
    std::shared_timed_mutex mutex;
    int state = 1;
    int old = 0;
    {
        std::unique_lock<std::shared_timed_mutex> lock(mutex);
        old = std::exchange(state, 2);
    }
    {
        std::shared_lock<std::shared_timed_mutex> lock(mutex);
        std::cout << "old=" << old << ", current=" << state << '\n';
    }
}
```

程序输出 `old=1, current=2`。读写锁只在读操作占绝大多数、临界区足以抵消额外协调成本时可能更有优势；是否公平、是否让写者饥饿由实现和工作负载共同决定。

## 共享互斥模型

`shared_timed_mutex` 有两种互斥的所有权模式：任意时刻要么一个线程持有独占锁，要么一个或多个线程持有共享锁。写者使用 `unique_lock`，读者使用 `shared_lock`。它还提供 `try_lock_for`、`try_lock_until` 等定时接口。

实现通常维护读者计数、写者状态和等待队列，内部成本高于普通互斥量。标准不保证严格公平，持续读流可能让写者饥饿，具体策略取决于平台实现。读临界区很短时，读者计数的共享缓存行竞争甚至可能比普通互斥量更慢。

共享锁只允许逻辑只读操作。如果所谓“读”会更新缓存、统计或延迟初始化状态，它仍可能需要独占锁或独立原子同步。返回受保护对象的引用后立即释放锁，也会把数据竞争推给调用者。

同一线程不能默认对 `shared_timed_mutex` 递归加锁，无论共享还是独占组合。标准没有递归共享互斥量；再次请求可能死锁或违反前置条件。把锁所有权集中在外层，内部 helper 接收“已持锁”状态而不重复获取。

共享所有权允许不同线程各持一个 `shared_lock`，但任何独占请求必须等所有读者释放。反过来独占持有期间读者和其他写者都不能进入。互斥量对象本身必须比所有锁包装器活得久。

### `shared_lock` 所有权接口

`shared_lock` 类似 `unique_lock` 的共享模式 RAII 包装：支持默认/延迟/尝试/定时/采用锁构造、移动所有权、`owns_lock()`、`operator bool`、`lock/try_lock/unlock`、`release` 和 `swap`。它不可复制。

`release()` 只放弃包装器与 mutex 的关联，不调用 `unlock_shared`；调用者必须接管解锁责任。它不是普通提前解锁。需要提前释放通常直接 `unlock()`，保留对象但状态变为不拥有。

`adopt_lock` 要求当前线程已以共享模式持锁，否则前置条件被破坏。`defer_lock` 只关联不获取，适合稍后协调；`try_to_lock` 立即尝试并可通过 `owns_lock` 检查。

### 锁接口与 RAII 包装

独占模式提供 `lock()`、`try_lock()`、`try_lock_for()`、`try_lock_until()` 和 `unlock()`；共享模式对应 `lock_shared()`、`try_lock_shared()`、`try_lock_shared_for()`、`try_lock_shared_until()` 和 `unlock_shared()`。实际代码应优先让 `unique_lock` 或 `shared_lock` 管理解锁，避免异常和提前返回破坏配对。

定时接口的失败只表示在给定等待条件内没有获得锁，不说明持锁线程已经发生故障。`try_lock_for` 接受相对时长，可能因为调度或系统时钟粒度等待得比请求更久；`try_lock_until` 接受绝对时间点。超时路径必须由业务显式定义，例如返回旧快照、重试、取消请求或报告繁忙。

标准不提供从共享所有权直接原子升级为独占所有权的操作。先释放共享锁再获取独占锁会留下竞争窗口，期间状态可能改变，因此写入前必须重新检查前置条件。反向“降级”也不应假定能无缝完成。

`try_lock_for(duration)` 使用相对等待，`try_lock_until(time_point)` 使用绝对截止时间；共享版本在名称中带 `_shared`。允许虚假失败的具体接口语义要按标准读取，即便未到超时也不应把失败解释为锁永久不可用。

`steady_clock` 截止更适合相对业务超时，`system_clock` 可能因系统校时跳变。实现可将时钟转换到内部等待原语，实际返回会受调度延迟影响，超时是“不早于/尽力”边界而非实时保证。

超时后绝不能访问受保护数据。常见 API 返回 optional 快照、错误码或 bool，让调用者决定重试/降级。把超时当作获得了“弱一致读”会直接造成数据竞争。

### 内存同步而非只保护语句块

写线程在独占解锁前对受保护数据的修改，会通过随后成功获取相应互斥量的线程变得可见。锁的作用既是排他，也是建立跨线程的 happens-before 关系。仅仅把字段声明为 `volatile` 不能替代这种同步。

共享模式允许多个读线程并发，但它们仍会共同更新互斥量内部的读者计数。高核心数下，这个计数可能成为缓存一致性热点。所以“读多写少”只是使用读写锁的必要线索，不是性能结论；还要比较临界区工作量与锁管理成本。

## `exchange` 的语义

`std::exchange(object, new_value)` 概念上先移动保存旧值，再把新值转发赋给对象，最后返回旧值。它把状态替换写成单个清晰表达式，但不是 CPU 原子交换；并发对象需要 `atomic::exchange`。

该工具常用于移动构造：目标取得源句柄，同时把源句柄设为空值；也适合状态机返回前一状态。它要求旧值可移动构造且新值可赋值，异常保证取决于这两个操作。

可以把它理解为如下三个有顺序的步骤：先从 `object` 构造旧值临时量，再执行 `object = new_value`，最后返回旧值。第一步成功、第二步抛出时，对象是否改变取决于赋值运算自身的异常保证；`exchange` 不额外提供事务回滚。返回类型是被替换对象的类型，而新值可以是能赋给它的不同类型。

概念签名让第二参数类型 U 默认等于 T，并以 U&& 接收，因此可写 `exchange(flag, false)`、`exchange(string, "new")`。新值经 forward 赋给 object，旧值经 move 构造返回。

它要求 T 可移动构造、T& 可由 U 赋值。对只能复制的旧类型，move 表达式仍可能落到复制构造；性能取决于 T。noexcept 性质由构造和赋值是否抛出决定，标准函数不会强行承诺不抛。

`exchange(x, x)` 或让 `new_value` 引用 object/其子对象时会出现别名与求值语义，先保存旧值后再赋值仍可能从已移动 object 读取。避免自别名，或先在外部构造独立新值。

```cpp example id="cpp14-exchange-move-state" std="c++14" file="main.cpp" kind="single" compilers="all" output="moved=7, source=-1"
#include <iostream>
#include <utility>

class Handle {
public:
    explicit Handle(int value) noexcept : value_(value) {}

    Handle(Handle&& other) noexcept
        : value_(std::exchange(other.value_, invalid_value)) {}

    Handle& operator=(Handle&& other) noexcept {
        if (this != &other) {
            value_ = std::exchange(other.value_, invalid_value);
        }
        return *this;
    }

    int value() const noexcept { return value_; }

private:
    static constexpr int invalid_value = -1;
    int value_;
};

constexpr int Handle::invalid_value;

int main() {
    Handle source(7);
    Handle moved(std::move(source));
    std::cout << "moved=" << moved.value()
              << ", source=" << source.value() << '\n';
}
```

移动构造函数取得旧句柄并同时把源对象设成明确的无效状态。这个例子没有真实资源释放逻辑；生产级句柄类的移动赋值还必须先正确释放目标原有资源。若只是覆盖 `value_`，会泄漏目标此前拥有的操作系统句柄。

### `std::exchange` 与原子交换的区别

`std::exchange` 是普通泛型函数，适用于任意满足构造和赋值要求的对象，不提供线程安全。`atomic<T>::exchange` 是原子读-改-写操作，可指定内存序，并参与原子对象的修改顺序。两者名字相似，但解决的问题分别是“简洁表达状态替换”和“并发同步”。

## 何时选择哪一种互斥量

若所有访问都需要写入，或临界区非常短，`mutex` 往往更简单且更快。只有读操作可真正并行、写入相对稀少、读取工作量足以摊薄内部计数成本时，才值得基准测试 `shared_timed_mutex`。若完全不需要超时，而工具链支持后续标准，可考虑 C++17 的 `shared_mutex`，它不承诺定时接口，允许实现针对这一较小接口优化。

无论选择哪种锁，都应把受保护数据和互斥量封装在同一抽象内。调用者不应拿到脱离锁生命周期的引用、指针或迭代器。需要长时间消费数据时，常见策略是在锁内复制快照，随后在锁外处理。

## 透明比较器与异构查找

C++14 标准关联容器支持在比较器透明时用不同于 `key_type` 的查询类型执行 find/`lower_bound` 等操作。`std::less<>`（即 `less<void>`）会转发实际参数类型，并声明透明能力，避免为查询临时构造完整键。

```cpp example id="cpp14-heterogeneous-lookup" std="c++14" file="main.cpp" kind="single" compilers="all" output="answer=42"
#include <iostream>
#include <map>
#include <string>

int main() {
    const std::map<std::string, int, std::less<>> values{{"answer", 42}};
    const auto iterator = values.find("answer");
    if (iterator == values.end()) {
        return 1;
    }
    std::cout << iterator->first << '=' << iterator->second << '\n';
}
```

查询参数是字符数组退化的 const char*，比较器能直接与 string 做关系比较，因此无需在调用点显式创建 string。是否真正零分配还取决于比较运算实现；自定义键应为两个方向提供一致严格弱序。

C++20 才加入 contains，C++14 使用 find。无序容器的通用异构查找属于后续演进，不能从有序容器规则类推。

## `quoted` 与类型萃取补充

`std::quoted`（`<iomanip>`）为流式字符串输入输出处理引号和转义字符。输出可选择分隔符/转义符，输入能恢复含空格文本。它仍受流 locale/状态影响，不是 JSON 或通用协议编码器。

C++14 `get<T>(tuple)` 可按类型取得 tuple 元素，但要求该类型在 tuple 中恰好出现一次；重复类型应继续按索引 get。它让语义唯一的异构记录少依赖位置，却不提供运行期按类型搜索。

类型萃取增加 `is_final`、`is_null_pointer` 等能力，并提供常用 `_t` 别名如 `remove_reference_t`、`enable_if_t`，减少 typename/type 样板。`_v` 变量模板便利形式到 C++17 才标准化。

这些增强看似零散，但都应按接口边界使用：quoted 解决流 token 转义，透明比较解决查找构造，萃取别名解决模板拼写；不要把它们堆进业务代码而不说明语义。

## 示例解析与工程权衡

示例在独占锁内用 `exchange` 更新状态，再在共享锁内读取。锁建立必要的同步关系，`exchange` 只负责值替换。评估读写锁时应测量实际读写比例、临界区时长和目标平台，并明确超时后业务如何恢复，而不是把定时锁当作自动容错。

## 接口级补充

### 库接口速查

| 接口 | 关键语义 |
| --- | --- |
| `lock_shared` | 阻塞取得共享所有权 |
| `try_lock_shared` | 不阻塞尝试共享锁，失败返回 false |
| `try_lock_shared_for` | 在相对时长内尝试共享锁 |
| `try_lock_shared_until` | 尝试到绝对截止时间 |
| `shared_lock` | 共享模式 RAII 所有者，可移动不可复制 |
| `defer_lock` | 关联互斥量但暂不拥有 |
| `adopt_lock` | 采用调用者已经持有的共享锁 |
| `exchange(obj,new)` | 返回旧值并赋新值，不提供同步或回滚 |
| 透明 `less<>` | 可让有序容器异构比较，避免部分临时键 |
| `quoted` | 流式定界/转义代理，不是完整数据格式解析器 |

`shared_timed_mutex` 的独占定时接口为 `try_lock_for/until`，共享接口为 `try_lock_shared_for/until`。相对超时接收 duration，绝对截止接收 `time_point`；调度延迟可能使函数晚于截止返回，它不是硬实时保证。

`shared_lock` 只有在底层互斥量支持对应协议时才能使用定时成员。`defer_lock` 建立关联但不获取，`adopt_lock` 则要求调用方已经以共享模式持锁；标签不会动态验证前置条件。

`std::exchange` 先移动/复制旧值，再把新值转发赋给对象。若赋值阶段抛出，它不提供事务回滚；条件 noexcept 取决于旧值构造和新值赋值两部分。它也是普通操作，不具备 atomic::exchange 的同步语义。

`std::quoted` 返回流代理，按指定定界符/转义符处理简单字符串，并不覆盖 CSV、JSON 的完整语法。代理通常只适合紧邻流表达式使用，不应越过其引用字符串生命周期保存。

C++14 的 `_t` 类型别名只缩短 `typename trait<T>::type` 写法，不改变 SFINAE 发生位置。底层 `::type` 不存在时，究竟安静替换失败还是硬错误仍由使用语境决定。

## C++14 库增强专项审查

- 读写比例是否真能让 `shared_timed_mutex` 获益？
- 定时锁晚于截止返回是否能被业务接受？
- `shared_lock` 的底层 mutex 是否支持所用定时接口？
- `adopt_lock` 前是否已经以共享模式拥有锁？
- 是否错误假定读写锁公平？
- exchange 的赋值异常是否会留下可接受状态？
- exchange 是否被误当作原子同步操作？
- 透明比较是否对查询类型与 key 双向一致？
- quoted 是否被误当作完整 CSV/JSON 解析？
- `_t` 别名错误是否位于期望的 SFINAE 语境？

## 权威资料

- [N3659：共享互斥量](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2013/n3659.html)
- [CPP14 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1319r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
