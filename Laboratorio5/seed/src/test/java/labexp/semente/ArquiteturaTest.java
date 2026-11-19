package labexp.semente;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;
import static com.tngtech.archunit.library.dependencies.SlicesRuleDefinition.slices;

import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;

@AnalyzeClasses(packages = "labexp.semente", importOptions = ImportOption.DoNotIncludeTests.class)
class ArquiteturaTest {

    @ArchTest
    static void domainNaoDependeDeNada(JavaClasses classes) {
        classes().that().resideInAPackage("labexp.semente.domain..")
                .should().onlyDependOnClassesThat()
                .resideInAnyPackage("labexp.semente.domain..", "java..")
                .check(classes);
    }

    @ArchTest
    static void applicationDependeSoDeDomain(JavaClasses classes) {
        classes().that().resideInAPackage("labexp.semente.application..")
                .should().onlyDependOnClassesThat()
                .resideInAnyPackage("labexp.semente.application..", "labexp.semente.domain..", "java..")
                .check(classes);
    }

    @ArchTest
    static void entradaESaidaIndependentes(JavaClasses classes) {
        noClasses().that().resideInAPackage("labexp.semente.adapter.in..")
                .should().dependOnClassesThat().resideInAPackage("labexp.semente.adapter.out..")
                .check(classes);
        noClasses().that().resideInAPackage("labexp.semente.adapter.out..")
                .should().dependOnClassesThat().resideInAPackage("labexp.semente.adapter.in..")
                .check(classes);
    }

    @ArchTest
    static void semCiclosEntrePacotes(JavaClasses classes) {
        slices().matching("labexp.semente.(*)..").should().beFreeOfCycles().check(classes);
        slices().matching("labexp.semente.adapter.(*)..").should().beFreeOfCycles().check(classes);
    }

    @ArchTest
    static void controladoresNaoAcessamRepositorios(JavaClasses classes) {
        noClasses().that().resideInAPackage("labexp.semente.adapter.in.web..")
                .should().dependOnClassesThat().resideInAnyPackage(
                        "labexp.semente.application.port.out..",
                        "labexp.semente.adapter.out..",
                        "org.springframework.data..")
                .check(classes);
    }
}
