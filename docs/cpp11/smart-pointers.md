# 智能指针

智能指针把资源生命周期绑定到对象生命周期。`unique_ptr` 表示独占所有权，`shared_ptr` 表示共享所有权，`weak_ptr` 用于非拥有观察并打破共享环。

<!-- example id="cpp11-smart-pointers" std="c++11" file="main.cpp" kind="single" compilers="all" output="value=42 owners=2" -->
```cpp
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
