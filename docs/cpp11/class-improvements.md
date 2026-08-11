# 类定义能力增强

C++11 可以显式默认或删除特殊成员函数，并通过 `override`、`final` 让继承意图接受编译器检查。委托构造和继承构造减少了重复初始化逻辑，`enum class` 避免枚举值污染外围作用域。

<!-- example id="cpp11-class-improvements" std="c++11" file="main.cpp" kind="single" compilers="all" output="worker:7" -->
```cpp
#include <iostream>
#include <string>

enum class Role { guest, worker };

class Entity {
public:
    explicit Entity(int id) : id_(id) {}
    virtual ~Entity() = default;
    virtual std::string name() const = 0;
    int id() const { return id_; }

private:
    int id_;
};

class Worker final : public Entity {
public:
    using Entity::Entity;
    std::string name() const override { return "worker"; }
    Worker(const Worker&) = delete;
    Worker& operator=(const Worker&) = delete;
};

int main() {
    Worker worker(7);
    const Role role = Role::worker;
    if (role == Role::worker) {
        std::cout << worker.name() << ':' << worker.id() << '\n';
    }
}
```

对所有虚函数重写使用 `override`。只有明确禁止继承或重写时才使用 `final`。删除函数不仅适用于复制操作，也可用于阻止不希望发生的隐式类型转换。

