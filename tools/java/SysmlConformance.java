// Conformance helper for the OMG SysML v2 Pilot Implementation.
//
// Usage: java -cp <pilot-jar>:<build-dir> SysmlConformance <library-dir>
//            <file.sysml>...
//
// Loads the standard library, reads all model files into one resource set
// so that cross-file references resolve, then validates each file. Prints
// one tab-separated line per issue:
//
//     ISSUE <severity> <file> <line> <column> <message>
//
// and a final line "DONE <files> <issues>". tools/sysml_conformance.py
// builds this class, runs it and formats the output.

import java.io.File;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.emf.ecore.util.EcoreUtil;
import org.eclipse.xtext.resource.XtextResource;
import org.eclipse.xtext.util.CancelIndicator;
import org.eclipse.xtext.validation.CheckMode;
import org.eclipse.xtext.validation.IResourceValidator;
import org.eclipse.xtext.validation.Issue;
import org.omg.sysml.interactive.SysMLInteractive;

public final class SysmlConformance {
    private SysmlConformance() {
    }

    private static String clean(String text) {
        if (text == null) {
            return "";
        }
        return text.replace('\t', ' ').replace('\r', ' ').replace('\n', ' ');
    }

    public static void main(String[] args) throws Exception {
        PrintStream out = new PrintStream(
            System.out, true, StandardCharsets.UTF_8
        );
        if (args.length < 2) {
            out.println("usage: SysmlConformance <library-dir> <file>...");
            System.exit(2);
        }
        // The Pilot prints progress messages to stdout; keep our channel
        // clean by sending them to stderr.
        System.setOut(System.err);

        SysMLInteractive pilot = SysMLInteractive.createInstance();
        pilot.setVerbose(false);
        pilot.loadLibrary(args[0]);

        List<Resource> inputs = new ArrayList<>();
        int issueCount = 0;
        for (int i = 1; i < args.length; i++) {
            String path = new File(args[i]).getAbsolutePath();
            try {
                Resource resource = pilot.readResource(path);
                pilot.addInputResource(resource);
                inputs.add(resource);
            } catch (RuntimeException e) {
                out.println(
                    "ISSUE\tERROR\t" + path + "\t0\t0\t"
                        + clean("Cannot load file: " + e.getMessage())
                );
                issueCount++;
            }
        }
        for (Resource resource : inputs) {
            EcoreUtil.resolveAll(resource);
        }
        for (Resource resource : inputs) {
            String path = resource.getURI().toFileString();
            IResourceValidator validator = ((XtextResource) resource)
                .getResourceServiceProvider()
                .getResourceValidator();
            List<Issue> issues = validator.validate(
                resource, CheckMode.ALL, CancelIndicator.NullImpl
            );
            for (Issue issue : issues) {
                Integer line = issue.getLineNumber();
                Integer column = issue.getColumn();
                out.println(
                    "ISSUE\t" + issue.getSeverity() + "\t" + path + "\t"
                        + (line == null ? 0 : line) + "\t"
                        + (column == null ? 0 : column) + "\t"
                        + clean(issue.getMessage())
                );
                issueCount++;
            }
        }
        out.println("DONE\t" + (args.length - 1) + "\t" + issueCount);
        out.flush();
        System.exit(0);
    }
}
