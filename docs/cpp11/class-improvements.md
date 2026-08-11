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

## 显式表达编译器生成行为

特殊成员函数包括默认构造、析构、复制构造、复制赋值、移动构造和移动赋值。过去开发者常声明私有但不实现的复制函数来禁止复制，错误直到链接或访问检查才暴露。`= delete` 把禁用行为放进重载集合，并在调用点给出明确编译错误。

`= default` 要求编译器按语言规则生成函数，同时允许开发者控制可见性、虚函数性质或声明位置。显式默认并不保证函数一定可用：若成员本身不可复制，对应默认复制函数仍会被定义为删除。

声明某些特殊成员会抑制其他成员的隐式生成。例如用户声明析构函数通常意味着编译器不再隐式生成移动操作。资源类应逐项审查，或更优先把资源交给标准 RAII 成员，遵循零法则。

## 虚函数检查的底层意义

没有 `override` 时，参数 cv 限定、引用限定或拼写差异可能让派生类意外声明新虚函数。`override` 使编译器验证基类确有可覆盖槽位；它通常不改变虚表布局或调用成本，只增加静态检查。

`final` 允许编译器知道某个类不能再派生或某个虚函数不能再覆盖。在可见动态类型的优化场景，编译器可能据此去虚拟化，但性能不是使用 `final` 的主要理由，设计约束才是。

## 构造函数复用

委托构造让一个构造函数调用同类的另一个构造函数，集中维护不变量；完成被委托构造后才执行当前构造函数体。委托链不能形成环。

`using Base::Base` 把基类构造函数引入派生类重载集合，但不会自动解决派生类新增成员的业务初始化。新增成员仍按默认成员初始化器或默认初始化规则处理。

## `enum class` 的类型安全

作用域枚举的枚举项必须通过 `Role::worker` 访问，不会泄漏到外围作用域，也不会隐式转换为整数。底层整数类型可显式指定，便于协议布局；转成整数必须使用显式转换。

## 示例解析与检查清单

示例把抽象基类析构设为虚函数，用 `override` 锁定重写关系，以 `final` 表达 Worker 不再作为扩展点，并删除复制操作表达身份对象不可复制。设计类时应分别回答：它是否拥有资源、能否复制、移动后状态如何、是否用于多态删除、继承是否真的是稳定扩展机制。
