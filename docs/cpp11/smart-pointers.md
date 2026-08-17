# 智能指针

智能指针把资源生命周期绑定到对象生命周期。`unique_ptr` 表示独占所有权，`shared_ptr` 表示共享所有权，`weak_ptr` 用于非拥有观察并打破共享环。

## 本章学习目标

完成本章后，应当能够：

- 根据业务所有权选择 `unique_ptr`、`shared_ptr`、`weak_ptr` 或普通引用。
- 解释三个智能指针的典型内存表示、析构路径和移动/复制成本。
- 说明 `shared_ptr` 控制块中的强弱引用计数如何配合。
- 正确使用工厂函数、自定义删除器、别名构造和 `enable_shared_from_this`。
- 区分“控制块线程安全”与“被管理对象线程安全”。
- 识别重复控制块、共享环、悬空观察者和错误资源删除方式。

## 先理解所有权

所有权回答“谁负责最终释放资源”。它与“谁可以访问对象”不是同一问题。一个对象可以有许多观察者，却只有一个所有者；也可以确实由多个组件共同决定生命周期。

函数签名应尽量表达这种关系：

| 参数形式 | 常见所有权含义 |
| --- | --- |
| `std::unique_ptr<T>` | 调用方把独占所有权转交给函数 |
| `std::unique_ptr<T>&` | 函数可能重置或转移调用方的所有权 |
| `const std::unique_ptr<T>&` | 观察所有者包装器，通常不是最佳只读业务参数 |
| `std::shared_ptr<T>` | 函数取得一份共享所有权，可能延长生命周期 |
| `const std::shared_ptr<T>&` | 暂时观察共享句柄，不增加引用计数 |
| `std::weak_ptr<T>` | 保存非拥有关系，使用时必须尝试锁定 |
| `T&` / `const T&` | 只在调用期间使用对象，不改变所有权 |
| `T*` | 可为空的非拥有观察，除非接口另有明确契约 |

如果函数只在调用期间读取 `T`，传 `const T&` 通常比传智能指针更好。这样函数不依赖调用方采用哪一种所有权策略。

## `unique_ptr`：独占所有权

### 核心语义

`unique_ptr<T, Deleter>` 在任意时刻独占一个资源。它不能复制，但可以移动；移动后源指针为空或处于明确的无所有权状态。析构、`reset` 或移动赋值覆盖旧资源时，会调用删除器。

独占所有权特别适合：

- 树节点和明确父子生命周期。
- PImpl 实现对象。
- 工厂函数返回新对象。
- 把资源装入容器。
- 在模块之间一次性移交资源。

### 典型内存表示

默认删除器的 `unique_ptr<T>` 通常只包含一个 `T*`。无状态删除器可借助空基类优化不增加对象大小，因此常见实现满足 `sizeof(unique_ptr<T>) == sizeof(T*)`，但这不是跨所有实现的强制保证。

有状态删除器会作为对象状态保存，可能让 `unique_ptr` 变成两个或更多机器字。删除器类型属于 `unique_ptr` 类型的一部分，所以不同删除器的 `unique_ptr` 默认不是同一种类型。

### 主要类型和工厂

| 接口 | 作用 | 注意事项 |
| --- | --- | --- |
| `std::unique_ptr<T>` | 管理单个对象 | 析构调用 `delete` |
| `std::unique_ptr<T[]>` | 管理动态数组 | 析构调用 `delete[]`，提供 `operator[]` |
| `std::make_unique<T>(args...)` | 构造单对象 | C++14 引入；本章仓库为 C++11，所以主示例未使用 |
| `std::make_unique<T[]>(n)` | 构造值初始化数组 | 通常更推荐 `vector` 保存动态序列 |

### 常用成员接口

| 成员 | 语义 |
| --- | --- |
| `get()` | 返回裸指针但不释放所有权 |
| `operator*` / `operator->` | 访问被管理对象，要求非空 |
| `explicit operator bool()` | 判断是否持有对象 |
| `release()` | 放弃所有权并返回裸指针，不执行删除 |
| `reset(pointer)` | 删除旧资源并接管新资源 |
| `swap(other)` | 交换指针和删除器状态 |
| `get_deleter()` | 取得删除器引用 |

`release()` 是高风险接口。调用后必须立刻把返回值交给另一个明确所有者，否则会泄漏。若只是想销毁对象，应调用 `reset()`，不要 `release()` 后再手写 `delete`。

### 自定义删除器

智能指针不仅能管理 `new` 创建的对象。任何能表示为指针并具有确定释放操作的资源，都可以交给自定义删除器，例如 `FILE*`、操作系统句柄和第三方 C API 对象。

删除器必须与资源创建方式匹配：

| 创建方式 | 正确释放方式 |
| --- | --- |
| `new T` | `delete` |
| `new T[n]` | `delete[]` |
| `malloc` | `free` |
| `fopen` | `fclose` |
| 平台句柄创建函数 | 对应平台关闭函数 |

错误匹配不是普通逻辑错误，通常会导致未定义行为、堆损坏或资源泄漏。

下面的完整示例把删除动作和外部计数器绑定，验证删除器恰好执行一次：

```cpp example id="cpp11-unique-ptr-deleter" std="c++11" file="main.cpp" kind="single" compilers="all" output="value=42, deleted=1"
#include <iostream>
#include <memory>

struct CountingDeleter {
    int* deleted;

    void operator()(int* pointer) const noexcept {
        ++*deleted;
        delete pointer;
    }
};

int main() {
    int deleted = 0;
    {
        std::unique_ptr<int, CountingDeleter> value(
            new int(42), CountingDeleter{&deleted});
        std::cout << "value=" << *value;
    }
    std::cout << ", deleted=" << deleted << '\n';
}
```

删除器随 unique_ptr 一起移动。这里计数器必须比智能指针活得更久；真实资源删除器若保存外部引用，也要证明相同生命周期关系。

### 不完整类型与 PImpl

`unique_ptr` 可以在头文件中声明为指向不完整类型的成员，这使 PImpl 成为常见用法。但执行默认删除器的位置必须看到完整类型。通常把拥有类的析构函数声明在头文件、定义在能看到实现类定义的 `.cpp` 文件中。

### 移动和异常保证

移动通常只转移指针及删除器，并把源指针清空。若删除器移动可能抛异常，会影响 `unique_ptr` 和外层容器的异常保证。无状态、不可抛的删除器最容易获得廉价且安全的移动。

## `shared_ptr`：共享所有权

### 何时才需要共享

只有在多个参与者确实无法确定唯一所有者、且任意最后存活者都必须保持对象有效时，才需要 `shared_ptr`。它不是“更安全的裸指针”，也不应作为所有接口的默认参数。

典型场景包括：

- 异步任务与提交者生命周期解耦。
- 订阅者共同使用不可轻易归属单方的共享状态。
- 图结构中某些节点确实由多个根共同拥有。
- 缓存把对象交给外部使用，而缓存可以提前移除自己的引用。

### 对象指针与控制块

典型 `shared_ptr` 对象保存两个指针：一个是对外解引用的对象指针，另一个指向控制块。控制块通常包含：

- 强引用计数。
- 弱引用计数。
- 对象删除器。
- 控制块分配器。
- 可能直接内嵌的对象存储。
- 类型擦除后的销毁操作。

最后一个强引用消失时，被管理对象销毁；最后一个弱引用也消失后，控制块才销毁。弱计数的具体内部偏置方式属于实现细节，不能通过猜测计数值依赖它。

### `make_shared` 与直接构造

`make_shared<T>(args...)` 通常一次分配同时容纳控制块和 T，对象与计数数据局部性更好，也避免“对象已分配但控制块构造失败”的所有权窗口。

直接写 `shared_ptr<T>(new T(...))` 通常产生对象分配和控制块分配两次操作。它仍有合理用途：需要自定义删除器、接管已有资源，或希望对象在强计数归零时立即释放其大块内存，而控制块继续供长寿 `weak_ptr` 使用。

合并分配的权衡是：对象析构后，只要还有弱引用，包含对象存储的整块分配可能仍不能归还。大型对象、弱观察者寿命很长时应评估这一点。

### 主要成员和非成员接口

| 接口 | 作用 | 使用建议 |
| --- | --- | --- |
| `get()` | 返回存储指针 | 不改变计数，不应用它建立新控制块 |
| `use_count()` | 返回当前强所有者数量的快照 | 仅适合诊断，不用于并发业务判断 |
| `unique()` | 判断计数是否为一 | C++20 已移除，不应用于同步判断 |
| `reset()` | 放弃当前共享所有权 | 可能触发对象析构 |
| `owner_before()` | 按控制块所有权排序 | 可比较别名指针的所有者身份 |
| `static_pointer_cast` | 共享所有权的静态转换 | 语义接近 `static_cast` |
| `dynamic_pointer_cast` | 运行期安全向下转换 | 失败返回空共享指针 |
| `const_pointer_cast` | 调整 const 属性 | 必须保证底层对象允许修改 |
| `reinterpret_pointer_cast` | 重新解释存储指针 | C++17 引入，风险与 reinterpret_cast 类似 |

### 别名构造函数

别名 `shared_ptr` 可以与某个控制块共享所有权，却让 `get()` 指向另一个相关地址，例如对象的成员或数组中的元素。这解释了为什么“对象指针相同”与“所有者相同”是两套关系。

别名指针必须保证目标地址的有效期被共享所有者覆盖。若指向与所有者无关的临时对象，控制块仍存活也无法防止悬空。

### `enable_shared_from_this`

对象若继承 `enable_shared_from_this<T>`，可以在已经由合适 `shared_ptr` 管理后调用 `shared_from_this()`，取得共享同一控制块的新所有者。内部通常保存一个由首个共享所有者初始化的弱引用。

在对象尚未进入 `shared_ptr` 控制块时调用会失败；在构造函数中调用尤其危险。也不能通过对同一 `this` 再写 `shared_ptr<T>(this)` 来“修复”，那会建立第二控制块并最终重复删除。

下面的示例证明 `shared_from_this()` 返回的新指针与原指针共享同一个控制块：

```cpp example id="cpp11-enable-shared-from-this" std="c++11" file="main.cpp" kind="single" compilers="all" output="owners=2"
#include <iostream>
#include <memory>

class Session : public std::enable_shared_from_this<Session> {
public:
    std::shared_ptr<Session> share() {
        return shared_from_this();
    }
};

int main() {
    const std::shared_ptr<Session> first = std::make_shared<Session>();
    const std::shared_ptr<Session> second = first->share();
    std::cout << "owners=" << first.use_count() << '\n';
}
```

若把 `Session` 直接创建在栈上再调用 `share()`，内部弱引用没有被控制块初始化，调用会抛出 `std::bad_weak_ptr`。

### 线程安全的准确边界

不同 `shared_ptr` 实例共享同一控制块时，可以在多个线程复制、移动和销毁这些不同实例，引用计数维护不会数据竞争。这个保证不等于：

- 可以无同步地同时写同一个 `shared_ptr` 变量。
- 可以无同步地修改被管理对象。
- `use_count() == 1` 后对象就不会被其他线程访问。

C++20 提供 `atomic<shared_ptr<T>>` 专门支持共享指针变量的原子发布与交换；早期标准有对应自由原子函数。对象内部状态仍需自己的锁或原子策略。

### 引用计数成本

复制共享指针通常需要原子增加强计数，销毁需要原子减少，并在归零路径执行对象和控制块销毁。高并发下控制块缓存行可能成为争用点。把 `shared_ptr` 按值层层传递会产生不必要计数流量；只在需要延长生命周期时复制。

## `weak_ptr`：非拥有观察

### 设计目的

`weak_ptr` 指向 shared_ptr 控制块，但不增加强引用计数，因此不会阻止对象析构。它解决两类问题：

- 打破双向关系或图结构中的强所有权环。
- 在不知道对象是否仍存在时保存可检查观察者。

### 常用接口

| 接口 | 作用 | 注意事项 |
| --- | --- | --- |
| `lock()` | 尝试原子地取得 `shared_ptr` | 对象已销毁时返回空 |
| `expired()` | 查询强计数是否已归零 | 只是瞬时信息，不能替代 lock |
| `use_count()` | 返回强计数快照 | 只适合诊断 |
| `reset()` | 放弃对控制块的观察 | 可能释放最后一个弱控制块引用 |
| `owner_before()` | 比较控制块所有权顺序 | 可用作关联容器排序依据 |

正确使用模式是直接调用 `lock()` 并检查结果。先 `expired()`、再从 weak_ptr 构造 shared_ptr 存在检查与使用之间的竞态；其他线程可能在两步之间释放最后一个强所有者。

### 打破共享环

假设父对象强拥有子对象，子对象若再用 shared_ptr 强拥有父对象，父子计数互相支撑，外部引用全部消失后仍不能释放。通常把回指改成 weak_ptr：父到子表示生命周期所有权，子到父只是导航关系。

不是所有环都应机械挑一条边变弱。应先定义业务所有权图：根是谁、谁决定销毁、观察者失效后怎么响应。weak_ptr 只是表达结果的工具。

下面的父子关系把父到子定义为强所有权、子到父定义为弱观察。外部所有者离开后，两者都可以释放：

```cpp example id="cpp11-weak-ptr-cycle" std="c++11" file="main.cpp" kind="single" compilers="all" output="parent expired=true"
#include <iostream>
#include <memory>

struct Parent;

struct Child {
    std::weak_ptr<Parent> parent;
};

struct Parent {
    std::shared_ptr<Child> child;
};

int main() {
    std::weak_ptr<Parent> observer;
    {
        const std::shared_ptr<Parent> parent = std::make_shared<Parent>();
        parent->child = std::make_shared<Child>();
        parent->child->parent = parent;
        observer = parent;
    }

    std::cout << "parent expired=" << std::boolalpha
              << observer.expired() << '\n';
}
```

如果把 `Child::parent` 改成 `shared_ptr<Parent>`，父子会各自保持对方强计数，示例作用域结束后也不会析构。

### 控制块寿命

对象销毁后，weak_ptr 仍需知道“对象已经不存在”，所以控制块继续存活。最后一个 weak_ptr 离开后控制块才释放。大量长期失效的弱引用虽然不保留对象，仍会保留控制块并占用少量内存。

## 主示例逐步解析

```cpp example id="cpp11-smart-pointers" std="c++11" file="main.cpp" kind="single" compilers="all" output="value=42 owners=2"
#include <iostream>
#include <memory>

int main() {
    std::unique_ptr<int> unique(new int(42));
    std::shared_ptr<int> shared = std::move(unique);
    std::weak_ptr<int> observer = shared;

    if (std::shared_ptr<int> locked = observer.lock()) {
        std::cout << "value=" << *locked << " owners=" << locked.use_count() << '\n';
    }
}
```

1. `unique` 首先独占整数对象。
2. 移动构造 `shared` 后，`unique` 不再拥有对象。
3. `observer` 加入弱引用，但强所有者数量仍然是一。
4. `lock()` 成功后产生临时强所有者 `locked`，因此输出时强计数为二。
5. `locked` 离开作用域后计数回到一，`shared` 析构时整数销毁。
6. 随后 `observer` 析构，最后一个弱引用消失，控制块释放。

默认优先使用 `unique_ptr`，只有确有共同生命周期时才使用 `shared_ptr`。不要用同一个裸指针分别构造多个 `shared_ptr`。C++11 尚无 `make_unique`，它在 C++14 中加入；创建共享对象则应优先使用 `make_shared`。

## 所有权首先是接口语义

智能指针的关键不只是自动 `delete`，而是让函数签名表达所有权：按值接收 `unique_ptr` 表示转移，`const unique_ptr&` 表示观察该所有者本身，裸指针或引用通常表示非拥有访问；按值传递 `shared_ptr` 会增加共享所有者。

## `unique_ptr` 的表示与成本

默认删除器的 `unique_ptr<T>` 典型情况下只保存一个指针，移动时转移指针并清空源对象，析构时调用删除器。自定义删除器属于指针类型的一部分，可能增加对象大小；无状态删除器通常能借助空基类优化不占额外空间。

数组需要 `unique_ptr<T[]>`，它使用 `delete[]` 并提供下标访问。不要混用单对象和数组形式，也不要用智能指针管理并非由匹配分配函数获得的资源；文件、套接字等资源应提供对应删除器。

## `shared_ptr` 控制块

共享指针通常包含对象指针和控制块指针。控制块保存强引用计数、弱引用计数、删除器和可能的分配器。复制 `shared_ptr` 原子地增加强计数，最后一个强所有者释放对象；控制块要等最后一个 `weak_ptr` 也离开后才释放。

`make_shared` 通常一次分配同时放置控制块和对象，改善局部性并减少分配次数。但只要弱引用仍在，合并分配的整块内存可能不能归还；大型对象且弱引用长寿时，分开分配有时更合适。

引用计数操作线程安全不等于对象线程安全。多个线程可以安全复制不同 `shared_ptr` 实例，但通过它们访问同一对象仍需对象自己的同步策略。

## `weak_ptr` 与所有权环

双向关系若两端都持有 `shared_ptr`，强计数永远不会归零。应把“拥有”方向建成强引用，把观察或回指方向建成 `weak_ptr`。使用前调用 `lock()` 原子地尝试获得临时强所有者；先 `expired()` 再访问存在检查与使用之间的竞争。

## 常见错误与检查清单

- 从同一裸指针建立多个独立控制块会导致重复释放。
- 对栈对象构造默认 `shared_ptr` 会错误删除栈内存。
- 捕获 `shared_from_this()` 的长期回调可能形成自环。
- `use_count()` 只适合诊断，不能作为并发业务判断。
- 优先 `make_unique`/`make_shared`，边界处明确所有权，内部算法尽量使用引用或观察指针。

## 更完整的错误模式

### 重复控制块

下面的设计思想是错误的：从同一个裸地址分别创建两个 shared_ptr。两个控制块都认为自己是唯一所有权系统，最终会对同一地址释放两次。

正确做法是复制已有 shared_ptr，或从 weak_ptr 调用 lock，让所有强引用共享原控制块。

### 错误接管栈对象

默认 shared_ptr/unique_ptr 删除器会执行 `delete`。把栈对象地址交给它们，会在析构时对非动态分配地址调用 delete。非拥有访问应使用引用或裸指针。

### shared_ptr 自环

对象把指向自己的 shared_ptr 捕获进自身长期持有的回调，会形成自环。可捕获 weak_ptr，在调用时 lock，并为失效情况定义行为。

### 滥用 `get()`

`get()` 只提供临时互操作地址。不要长期保存而忽略所有者，不要手工 delete，不要用返回地址创建另一个默认 shared_ptr。

### 把引用计数当锁

计数只保护生命周期，不保护对象值。即使对象不会析构，两个线程并发修改普通成员仍然是数据竞争。

## 性能决策表

| 需求 | 首选方案 | 原因 |
| --- | --- | --- |
| 单一所有者 | `unique_ptr` | 指针级成本、可移动、所有权清晰 |
| 可空但不拥有 | `T*` | 不引入控制块或计数 |
| 不可空且不拥有 | `T&` | 类型直接表达必须存在 |
| 多方共同决定生命周期 | `shared_ptr` | 引用计数管理最后释放者 |
| 观察共享对象但不延寿 | `weak_ptr` | 可安全尝试取得临时所有者 |
| 高频只读调用 | `const T&` | 避免重复引用计数更新 |
| 多线程发布共享句柄 | 原子 shared_ptr 接口 | 同步指针变量本身 |

## API 设计建议

- 工厂返回 `unique_ptr`，调用方需要共享时可向 `shared_ptr` 移动转换。
- 不要仅因为对象“可能以后共享”就提前返回 shared_ptr。
- 函数按值接收 shared_ptr 表示它会保存或延长生命周期；否则考虑 `const T&`。
- 类成员使用 shared_ptr 前，在设计文档画出强所有权图。
- 对回调和异步任务明确捕获 shared_ptr 是延寿还是意外形成环。
- 跨动态库边界使用自定义删除器时，确保释放发生在匹配的运行库或模块。

## 测试策略

智能指针代码不能只测试正常访问，还应覆盖：

1. 空指针输入。
2. 移动后的源对象。
3. 构造过程中抛异常。
4. 自定义删除器恰好执行一次。
5. weak_ptr 在对象存活和销毁后的 lock。
6. 回调形成环后能否释放。
7. 多线程复制句柄与修改对象的同步边界。
8. 大对象配合长期 weak_ptr 的内存峰值。
9. PImpl 析构位置是否看到完整类型。
10. 接口返回异常或提前退出时资源是否仍释放。

可在测试对象的构造、析构中维护计数，并结合 AddressSanitizer、LeakSanitizer 和 ThreadSanitizer 检查重复释放、泄漏与数据竞争。

## 最终选择流程

1. 资源是否需要动态生命周期？若不需要，优先普通局部对象。
2. 是否存在唯一、明确的所有者？若是，使用 `unique_ptr`。
3. 其他代码是否只需要调用期间访问？传引用或观察指针。
4. 是否确实有多个独立参与者共同保持生命周期？才使用 `shared_ptr`。
5. 共享关系中是否存在回指或缓存观察？使用 `weak_ptr` 表达非拥有边。
6. 是否跨线程？分别设计句柄发布同步和对象内部同步。
7. 是否使用特殊资源？为创建方式配对正确删除器。

智能指针的最佳实践不是“把所有裸指针替换掉”，而是让所有权边界能够从类型和接口直接读出来。

## 三类智能指针接口对照

| 接口/性质 | `unique_ptr` | `shared_ptr` | `weak_ptr` |
| --- | --- | --- | --- |
| 所有权 | 唯一 | 共享强所有权 | 非拥有观察 |
| 复制 | 禁止 | 增加强计数 | 增加弱观察计数 |
| 移动 | 转移指针/删除器 | 转移一个共享句柄 | 转移观察句柄 |
| `get()` | 返回裸观察指针 | 返回裸观察指针 | 无直接 get |
| `release()` | 放弃所有权且不删除 | 不提供 | 不提供 |
| `reset()` | 删除旧对象并接管新值 | 释放当前强所有权 | 清除观察状态 |
| `use_count()` | 不适用 | 强计数快照，不用于同步决策 | 对应强计数快照 |
| `lock()` | 不适用 | 不适用 | 原子尝试取得 shared_ptr |
| 自定义删除器 | 属于指针类型 | 存在控制块中 | 沿控制块观察 |
| 数组支持 | `unique_ptr<T[]>` | C++11 shared_ptr 数组接口需谨慎核对版本 | 跟随对应 shared 所有权 |
| 循环引用 | 不会形成共享环 | 可能泄漏 | 用于打断 shared 环 |
| 典型工厂 | `unique_ptr(new T)` / C++14 make_unique | `make_shared<T>` | 从 shared_ptr 构造 |

## 智能指针专项审查

- 所有权是唯一、共享还是只观察，类型是否准确表达？
- unique_ptr 自定义删除器是否匹配资源获取方式？
- 是否在 release 后立即把裸资源交给新 RAII 所有者？
- shared_ptr 是否从同一裸指针创建了两个控制块？
- make_shared 的对象与控制块共同分配寿命是否可接受？
- shared_ptr 别名构造是否保持正确所有者但指向子对象？
- enable_shared_from_this 是否只在对象已有 shared 控制块后调用？
- 回调/父子图是否因 shared_ptr 环永不释放？
- weak_ptr::lock 失败是否作为正常竞态处理？
- use_count 是否仅用于观察而非线程同步决策？

## 智能指针故障定位线索

- 对象析构从未发生：先画 shared_ptr 强引用图，寻找闭环。
- 对象提前析构：检查是否只保存 weak_ptr 或裸观察指针。
- double free：检查是否从同一裸指针独立构造多个 shared_ptr。
- bad_weak_ptr：检查 shared_from_this 调用时控制块是否已经建立。
- 删除函数不匹配：核对 new/new[]、C 获取函数与删除器配对。
- unique_ptr 无法放入容器：确认调用点使用移动且容器操作支持移动。
- use_count 波动：它只是并发快照，不能作为“现在安全独占”的判断。
- make_shared 后内存迟迟不归还：弱引用可能仍保留合并控制块分配。
- PImpl 编译报 incomplete type：把拥有类析构定义移到实现类型完整处。
- 异步回调悬空：根据语义捕获 shared 所有权或 weak 后在执行时 lock。

## 权威资料

- [智能指针库规范](https://eel.is/c++draft/mem)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
